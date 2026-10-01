"""Sends optimization results to the LCLS electronic logbook. Generates an
XML entry with run summary (gain, duration, algorithm) and attaches a
screenshot of the GUI for the facility archive."""

import logging
import os
from datetime import UTC, datetime

import elog_client

from badger.archive import BADGER_ARCHIVE_ROOT
from badger.errors import BadgerConfigError, BadgerLogbookError
from badger.settings import init_settings

logger = logging.getLogger(__name__)

# Check badger logbook root
config_singleton = init_settings()
BADGER_LOGBOOK_ROOT = config_singleton.read_value("BADGER_LOGBOOK_ROOT")
if BADGER_LOGBOOK_ROOT is None:
    raise BadgerConfigError("Please set the BADGER_LOGBOOK_ROOT env var!")
elif not os.path.exists(BADGER_LOGBOOK_ROOT):
    os.makedirs(BADGER_LOGBOOK_ROOT)
    logger.info(f"Badger logbook root {BADGER_LOGBOOK_ROOT} created")


def send_to_logbook(routine, widget=None):

    log_text = ""
    routine_name = routine.name
    generator_name = routine.generator.name
    data_path = BADGER_ARCHIVE_ROOT
    obj_name = routine.vocs.objective_names[0]
    env_name = routine.environment.name

    idx_opt, obj_opt, _ = routine.vocs.select_best(routine.sorted_data, n=1)
    idx_opt = int(idx_opt[0])
    obj_opt = obj_opt[0]

    data = routine.data
    obj_start = data[obj_name].iloc[0]
    duration = data["timestamp"].iloc[-1] - data["timestamp"].iloc[0]
    n_point = len(data["timestamp"])
    if n_point > 0:
        log_text = f"Gain ({obj_name}): {round(obj_start, 4)} -> {round(obj_opt, 4)}\n"
    log_text += f"Time cost: {round(duration, 2)}s\n"
    log_text += f"Points requested: {n_point}\n"
    log_text += f"Optimal solution index: {idx_opt}\n"
    log_text += f"Routine name: {routine_name}\n"
    log_text += f"Environment name: {env_name}\n"
    log_text += f"Optimization algorithm: {generator_name}\n"
    log_text += f"Data location: {data_path}\n"
    log_text += f"Log location: {BADGER_LOGBOOK_ROOT}\n"

    curr_time = datetime.now(tz=UTC)
    if os.name == "nt":
        timestr = curr_time.strftime("%Y-%m-%dT%H%M%S-00")
    else:
        timestr = curr_time.strftime("%Y-%m-%dT%H:%M:%S-00")
    file_name = os.path.join(BADGER_LOGBOOK_ROOT, f"{timestr}.png")
    desired_log = (
        "physics_lcls2elog"
        if "lcls2" in BADGER_LOGBOOK_ROOT
        else "physics_facetelog"
        if "facet" in BADGER_LOGBOOK_ROOT
        else "physics_lclselog"
    )

    screenshot(widget, file_name)
    elog_client.post(
        title="Badger", body=log_text, file_paths=[file_name], logbooks=[desired_log]
    )


def screenshot(widget, filename):
    """
    Takes a screenshot of the whole gui window, saves png and ps images to file
    """
    if widget is None:
        raise BadgerLogbookError("No widget to take screenshot on!")

    from PIL import Image

    pic = widget.grab()
    pic.save(filename)
    img = Image.open(filename)
    if img.mode in ("RGBA", "LA"):
        # https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html?highlight=eps#eps
        img = img.convert("RGB")
