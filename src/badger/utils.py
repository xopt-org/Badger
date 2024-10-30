from importlib import metadata
import json
import logging
import os
import sys
import pathlib
from datetime import datetime

import yaml

from badger.errors import BadgerLoadConfigError

logger = logging.getLogger(__name__)


# https://stackoverflow.com/a/39681672/4263605
# https://github.com/yaml/pyyaml/issues/234#issuecomment-765894586
class Dumper(yaml.Dumper):
    def increase_indent(self, flow=False, indentless=False):
        return super(Dumper, self).increase_indent(flow, False)


def get_yaml_string(content):
    if content is None:
        return ""

    return yaml.dump(content, Dumper=Dumper, default_flow_style=False, sort_keys=False)


def yprint(content):
    print(get_yaml_string(content), end="")


def norm(x, lb, ub):
    return (x - lb) / (ub - lb)


def denorm(x, lb, ub):
    return (1 - x) * lb + x * ub


def config_list_to_dict(config_list):
    if not config_list:
        return {}

    book = {}
    for config in config_list:
        for k, v in config.items():
            book[k] = v

    return book


def load_config(fname):
    configs = None

    if fname is None:
        return configs

    # if fname is a yaml string
    if not os.path.exists(fname):
        try:
            configs = yaml.safe_load(fname)
            # A string is also a valid yaml
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


def merge_params(default_params, params):
    merged_params = None

    if params is None:
        merged_params = default_params
    elif default_params is None:
        merged_params = params
    else:
        merged_params = {**default_params, **params}

    return merged_params


def range_to_str(vranges):
    # Transfer the range list to a string for better printing
    vranges_str = []
    for var_dict in vranges:
        var = next(iter(var_dict))
        vrange = var_dict[var]
        vranges_str.append({})
        vranges_str[-1][var] = f"{vrange[0]} -> {vrange[1]}"

    return vranges_str


def ts_to_str(ts, format="lcls-log"):
    if format == "lcls-log":
        return ts.strftime("%d-%b-%Y %H:%M:%S")
    elif format == "lcls-log-full":
        return ts.strftime("%d-%b-%Y %H:%M:%S.%f")
    elif format == "lcls-fname":
        return ts.strftime("%Y-%m-%d-%H%M%S")
    else:  # ISO format
        return ts.isoformat()


def str_to_ts(timestr, format="lcls-log"):
    if format == "lcls-log":
        return datetime.strptime(timestr, "%d-%b-%Y %H:%M:%S")
    elif format == "lcls-log-full":
        return datetime.strptime(timestr, "%d-%b-%Y %H:%M:%S.%f")
    elif format == "lcls-fname":
        return datetime.strptime(timestr, "%Y-%m-%d-%H%M%S")
    else:  # ISO format
        return datetime.fromisoformat(timestr)


def ts_float_to_str(ts_float, format="lcls-log"):
    ts = datetime.fromtimestamp(ts_float)
    return ts_to_str(ts, format)


def curr_ts():
    return datetime.now()


def curr_ts_to_str(format="lcls-log"):
    return ts_to_str(datetime.now(), format)


def get_header(routine):
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


def run_names_to_dict(run_names):
    runs = {}
    for name in run_names:
        tokens = name.split("-")
        year = tokens[1]
        month = tokens[2]
        day = tokens[3]

        try:
            year_dict = runs[year]
        except Exception:
            runs[year] = {}
            year_dict = runs[year]
        key_month = f"{year}-{month}"
        try:
            month_dict = year_dict[key_month]
        except Exception:
            year_dict[key_month] = {}
            month_dict = year_dict[key_month]
        key_day = f"{year}-{month}-{day}"
        try:
            day_list = month_dict[key_day]
        except Exception:
            month_dict[key_day] = []
            day_list = month_dict[key_day]
        day_list.append(name)

    return runs


def convert_str_to_value(str):
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


def parse_rule(rule):
    if type(rule) is str:
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


def get_value_or_none(book, key):
    try:
        value = book[key]
    except KeyError:
        value = None

    return value


def dump_state(dump_file, generator, data):
    """dump data to file"""
    if dump_file is not None:
        output = state_to_dict(generator, data)
        with open(dump_file, "w") as f:
            yaml.dump(output, f)
        logger.debug(f"Dumped state to YAML file: {dump_file}")


def state_to_dict(generator, data, include_data=True):
    # dump data to dict with config metadata
    output = {
        "generator": {
            "name": type(generator).name,
            type(generator).name: json.loads(generator.model_dump_json()),
        },
        "vocs": json.loads(generator.vocs.model_dump_json()),
    }
    if include_data:
        output["data"] = json.loads(data.to_json())

    return output


# https://stackoverflow.com/a/18472142
def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).
    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    try:
        val = val.lower()
    except AttributeError:
        return val

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
