import os
import time
import warnings
import logging

from badger.utils import ts_float_to_str
from badger.settings import init_settings
from badger.routine import Routine
from badger.errors import BadgerConfigError

logger = logging.getLogger(__name__)


# Check badger optimization run archive root
config_singleton = init_settings()
BADGER_ARCHIVE_ROOT = config_singleton.read_value("BADGER_ARCHIVE_ROOT")
if BADGER_ARCHIVE_ROOT is None:
    raise BadgerConfigError("Please set the BADGER_ARCHIVE_ROOT env var!")
elif not os.path.exists(BADGER_ARCHIVE_ROOT):
    os.makedirs(BADGER_ARCHIVE_ROOT)
    logger.info(f"Badger run root {BADGER_ARCHIVE_ROOT} created")


def archive_run(routine, states=None):
    # routine: Routine

    data = routine.sorted_data
    data_dict = data.to_dict("list")
    if hasattr(routine, "creation_ts"):
        suffix = routine.creation_ts
    else:  # compatibility with old routines
        ts_float = data_dict["timestamp"][0]  # time of the first evaluated point
        suffix = ts_float_to_str(ts_float, "lcls-fname")
    tokens = suffix.split("-")
    first_level = tokens[0]
    second_level = f"{tokens[0]}-{tokens[1]}"
    third_level = f"{tokens[0]}-{tokens[1]}-{tokens[2]}"
    path = os.path.join(BADGER_ARCHIVE_ROOT, first_level, second_level, third_level)
    env_name = routine.environment.name
    # algo_name = routine.generator.name
    fname = f"{env_name}-{suffix}.yaml"

    run = {
        "filename": fname,
        "routine": routine,
        "data": data_dict,
    }
    if states:  # save the system states
        run["system_states"] = states

    os.makedirs(path, exist_ok=True)
    routine.dump(os.path.join(path, fname))

    # Temporarily add path information
    # Do not save this info in database or on disk
    run["path"] = path

    return run


def clear_tmp_runs():
    path = os.path.join(BADGER_ARCHIVE_ROOT, ".tmp")
    if os.path.exists(path):
        for f in os.listdir(path):
            os.remove(os.path.join(path, f))


def save_tmp_run(routine):
    # routine: Routine
    path = os.path.join(BADGER_ARCHIVE_ROOT, ".tmp")
    suffix = time.strftime("%Y-%m-%d-%H%M%S")
    fname = f".tmp-BadgerOpt-{suffix}.yaml"

    os.makedirs(path, exist_ok=True)
    routine.dump(os.path.join(path, fname))

    return fname


def list_run():
    runs = {}
    # Get years, latest first
    years = sorted(
        [
            p
            for p in os.listdir(BADGER_ARCHIVE_ROOT)
            if os.path.isdir(os.path.join(BADGER_ARCHIVE_ROOT, p))
        ],
        reverse=True,
    )
    for year in years:
        path_year = os.path.join(BADGER_ARCHIVE_ROOT, year)
        months = sorted(
            [
                p
                for p in os.listdir(path_year)
                if os.path.isdir(os.path.join(path_year, p))
            ],
            reverse=True,
        )
        runs[year] = {}
        for month in months:
            path_month = os.path.join(path_year, month)
            days = sorted(
                [
                    p
                    for p in os.listdir(path_month)
                    if os.path.isdir(os.path.join(path_month, p))
                ],
                reverse=True,
            )
            runs[year][month] = {}
            for day in days:
                path_day = os.path.join(path_month, day)
                files = [
                    p for p in os.listdir(path_day) if os.path.splitext(p)[1] == ".yaml"
                ]
                files = sorted(
                    files,
                    key=lambda f: os.path.getmtime(os.path.join(path_day, f)),
                    reverse=True,
                )
                runs[year][month][day] = files

    return runs


def get_runs():
    runs = list_run()
    run_list = []
    for year, months in runs.items():
        for month, days in months.items():
            for day, files in days.items():
                for run_fname in files:
                    run_list.append(run_fname)

    return run_list


def load_run(run_fname) -> Routine:
    if run_fname.startswith(".tmp"):  # temp run file
        filename = os.path.join(BADGER_ARCHIVE_ROOT, ".tmp", run_fname)
    else:
        tokens = run_fname.split("-")
        first_level = tokens[1]
        second_level = f"{tokens[1]}-{tokens[2]}"
        third_level = f"{tokens[1]}-{tokens[2]}-{tokens[3]}"

        filename = os.path.join(
            BADGER_ARCHIVE_ROOT, first_level, second_level, third_level, run_fname
        )

    # TODO: create utility function to catch warnings to remove code
    # duplication
    with warnings.catch_warnings(record=True) as caught_warnings:
        routine = Routine.from_file(filename)

        # Check if any user warnings were caught
        for warning in caught_warnings:
            if issubclass(warning.category, UserWarning):
                pass
            else:
                print(f"Caught warning: {warning.message}")

    return routine


def update_run(routine: Routine):
    pass


def delete_run(run_fname):
    tokens = run_fname.split("-")
    first_level = tokens[1]
    second_level = f"{tokens[1]}-{tokens[2]}"
    third_level = f"{tokens[1]}-{tokens[2]}-{tokens[3]}"

    prefix = os.path.join(BADGER_ARCHIVE_ROOT, first_level, second_level, third_level)

    # Try remove the pickle file (could exist or not)
    pickle_fname = os.path.splitext(run_fname)[0] + ".pickle"
    try:
        os.remove(os.path.join(prefix, pickle_fname))
    except FileNotFoundError:
        pass

    # Remove the yaml data file
    os.remove(os.path.join(prefix, run_fname))


def get_base_run_filename(run_filename):
    if run_filename.endswith(" (failed to load)"):
        base_name = run_filename[:-17]
    else:
        base_name = run_filename

    return base_name
