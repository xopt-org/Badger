from importlib import metadata
import json
import logging
import os
import sys
import pathlib
from datetime import datetime
from types import TracebackType
from typing import TYPE_CHECKING, Any, Iterable, Optional, TypedDict

from pandas import DataFrame
import yaml

from badger.errors import BadgerLoadConfigError
from PyQt5.QtWidgets import QWidget, QLayout

if TYPE_CHECKING:
    from xopt.generators import Generator
    from badger.routine import Routine

logger = logging.getLogger(__name__)


class BlockSignalsContext:
    widgets: Iterable[QWidget | QLayout]

    def __init__(self, widgets: QWidget | QLayout | Iterable[QWidget | QLayout]):
        if isinstance(widgets, Iterable):
            self.widgets = widgets
        else:
            self.widgets = [widgets]

    def __enter__(self):
        for widget in self.widgets:
            if widget.signalsBlocked():
                logger.warning(
                    f"Signals already blocked for {widget} when entering context. Nesting BlockSignalsContext is not recommended as blockSignals is set to False upon exiting the context. This may lead to unexpected behavior if the widget is used again from within another BlockSignalsContext."
                )
            widget.blockSignals(True)

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        exc_traceback: Optional[TracebackType],
    ):
        for widget in self.widgets:
            if not widget.signalsBlocked():
                logger.warning(
                    f"Signals not blocked for {widget} when exiting context. Nesting BlockSignalsContext is not recommended as blockSignals is set to False upon exiting the context. This may lead to unexpected behavior if the widget is used again from within another BlockSignalsContext."
                )
            widget.blockSignals(False)


# https://stackoverflow.com/a/39681672/4263605
# https://github.com/yaml/pyyaml/issues/234#issuecomment-765894586
class Dumper(yaml.Dumper):
    def increase_indent(self, flow: bool = False, indentless: bool = False):
        return super(Dumper, self).increase_indent(flow, False)


def get_yaml_string(content: Any) -> str:
    if content is None:
        return ""

    return yaml.dump(content, Dumper=Dumper, default_flow_style=False, sort_keys=False)


def yprint(content: Any) -> None:
    print(get_yaml_string(content), end="")


def norm(x: float, lb: float, ub: float) -> float:
    return (x - lb) / (ub - lb)


def denorm(x: float, lb: float, ub: float) -> float:
    return (1 - x) * lb + x * ub


def config_list_to_dict(
    config_list: Optional[Iterable[dict[str, Any]]],
) -> dict[str, Any]:
    if not config_list:
        return {}

    book: dict[str, Any] = {}
    for config in config_list:
        for k, v in config.items():
            book[k] = v

    return book


def load_config(fname: Optional[str]) -> Optional[dict[str, Any]]:
    configs = None

    if fname is None:
        return configs

    # if fname is a yaml string
    if not os.path.exists(fname):
        try:
            configs = yaml.safe_load(fname)  # A string is also a valid yaml
            if type(configs) is str:
                raise BadgerLoadConfigError(
                    f"Error loading config {fname}: file not found"
                )

            return configs
        except yaml.YAMLError:
            err_msg = f"Error parsing config {fname}: invalid yaml"
            raise BadgerLoadConfigError(err_msg)

    with open(fname, "r") as f:
        try:
            configs = yaml.safe_load(f)
        except yaml.YAMLError:
            err_msg = f"Error loading config {fname}: invalid yaml"
            raise BadgerLoadConfigError(err_msg)

    return configs


def merge_params(
    default_params: Optional[dict[str, Any]], params: Optional[dict[str, Any]]
) -> Optional[dict[str, Any]]:
    merged_params = None

    if params is None:
        merged_params = default_params
    elif default_params is None:
        merged_params = params
    else:
        merged_params = {**default_params, **params}

    return merged_params


def range_to_str(vranges: Iterable[dict[str, Any]]) -> list[dict[str, str]]:
    # Transfer the range list to a string for better printing
    vranges_str: list[dict[str, str]] = []
    for var_dict in vranges:
        var = next(iter(var_dict))
        vrange = var_dict[var]
        vranges_str.append({})
        vranges_str[-1][var] = f"{vrange[0]} -> {vrange[1]}"

    return vranges_str


def ts_to_str(ts: datetime, format: str = "lcls-log") -> str:
    if format == "lcls-log":
        return ts.strftime("%d-%b-%Y %H:%M:%S")
    elif format == "lcls-log-full":
        return ts.strftime("%d-%b-%Y %H:%M:%S.%f")
    elif format == "lcls-fname":
        return ts.strftime("%Y-%m-%d-%H%M%S")
    else:  # ISO format
        return ts.isoformat()


def str_to_ts(timestr: str, format: str = "lcls-log") -> datetime:
    if format == "lcls-log":
        return datetime.strptime(timestr, "%d-%b-%Y %H:%M:%S")
    elif format == "lcls-log-full":
        return datetime.strptime(timestr, "%d-%b-%Y %H:%M:%S.%f")
    elif format == "lcls-fname":
        return datetime.strptime(timestr, "%Y-%m-%d-%H%M%S")
    else:  # ISO format
        return datetime.fromisoformat(timestr)


def ts_float_to_str(ts_float: float, format: str = "lcls-log") -> str:
    ts = datetime.fromtimestamp(ts_float)
    return ts_to_str(ts, format)


def curr_ts() -> datetime:
    return datetime.now()


def curr_ts_to_str(format: str = "lcls-log") -> str:
    return ts_to_str(datetime.now(), format)


def create_archive_run_filename(routine: "Routine", format: str = "lcls-fname") -> str:
    data = routine.sorted_data
    env_name = routine.environment.name
    data_dict = data.to_dict("list")  # type: ignore
    ts_float = data_dict["timestamp"][0]  # time of the first evaluated point
    suffix = ts_float_to_str(ts_float, format)
    fname = f"{env_name}-{suffix}.yaml"
    return fname


def get_header(routine: "Routine") -> list[str]:
    try:
        obj_names = routine.vocs.objective_names
    except Exception:
        obj_names = []
    try:
        var_names = routine.vocs.variable_names
    except Exception:
        var_names = []
    try:
        con_names = routine.vocs.constraint_names
    except Exception:
        con_names = []
    try:
        sta_names = routine.vocs.constant_names
    except KeyError:
        sta_names = []

    return obj_names + con_names + var_names + sta_names


def run_names_to_dict(
    run_names: Iterable[str],
) -> dict[str, dict[str, dict[str, list[str]]]]:
    runs: dict[str, dict[str, dict[str, list[str]]]] = {}
    for name in run_names:
        name = os.path.basename(
            name
        )  # name is full path to run-file, so grab just the filename
        tokens = name.split("-")
        year = tokens[1]
        month = tokens[2]
        day = tokens[3]

        try:
            year_dict = runs[year]
        except KeyError:
            runs[year] = {}
            year_dict = runs[year]
        key_month = f"{year}-{month}"
        try:
            month_dict = year_dict[key_month]
        except KeyError:
            year_dict[key_month] = {}
            month_dict = year_dict[key_month]
        key_day = f"{year}-{month}-{day}"
        try:
            day_list = month_dict[key_day]
        except KeyError:
            month_dict[key_day] = []
            day_list = month_dict[key_day]
        day_list.append(name)

    return runs


def convert_str_to_value(str: str) -> Any:
    try:
        return int(str)
    except ValueError:
        pass

    try:
        return float(str)
    except ValueError:
        pass

    try:
        return bool(str)
    except ValueError:
        pass

    return str


class Rule(TypedDict):
    direction: str
    filter: str
    reducer: str


def parse_rule(rule: Rule | str) -> Rule:
    if isinstance(rule, str):
        return {
            "direction": rule,
            "filter": "ignore_nan",
            "reducer": "percentile_80",
        }

    # rule is a dict
    try:
        direction = rule["direction"]
    except Exception:
        direction = "MINIMIZE"
    try:
        filter = rule["filter"]
    except Exception:
        filter = "ignore_nan"
    try:
        reducer = rule["reducer"]
    except Exception:
        reducer = "percentile_80"

    return {
        "direction": direction,
        "filter": filter,
        "reducer": reducer,
    }


def get_value_or_none(book: dict[str, Any], key: str) -> Any:
    try:
        value = book[key]
    except KeyError:
        value = None

    return value


def dump_state(dump_file: str | None, generator: "Generator", data: DataFrame):
    """dump data to file"""
    if dump_file is not None:
        output = state_to_dict(generator, data)
        with open(dump_file, "w") as f:
            yaml.dump(output, f)
        logger.debug(f"Dumped state to YAML file: {dump_file}")


class StateDict(TypedDict, total=False):
    generator: dict[str, Any]
    vocs: dict[str, Any]
    data: Optional[dict[str, Any]]


def state_to_dict(
    generator: "Generator", data: DataFrame, include_data: bool = True
) -> StateDict:
    # dump data to dict with config metadata
    output: StateDict = {
        "generator": {
            "name": type(generator).name,
            type(generator).name: json.loads(generator.model_dump_json()),
        },
        "vocs": json.loads(generator.vocs.model_dump_json()),
    }
    if include_data:
        output["data"] = json.loads(data.to_json())  # type: ignore

    return output


# https://stackoverflow.com/a/18472142
def strtobool(val: str) -> bool:
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    try:
        val = val.lower()
    except AttributeError:
        return bool(val)

    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError("invalid truth value %r" % (val,))


# https://stackoverflow.com/a/61901696/4263605
def get_datadir() -> pathlib.Path:
    """
    Returns a parent directory path
    where persistent application data can be stored.

    # linux: ~/.local/share
    # macOS: ~/Library/Application Support
    # windows: C:/Users/<USER>/AppData/Roaming
    """

    home = pathlib.Path.home()

    if sys.platform == "win32":
        return home / "AppData/Roaming"
    elif sys.platform == "linux":
        return home / ".local/share"
    elif sys.platform == "darwin":
        return home / "Library/Application Support"


def get_badger_version():
    return metadata.version("badger-opt")


def get_xopt_version():
    return metadata.version("xopt")
