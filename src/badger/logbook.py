import os
from datetime import datetime
import logging

from badger.settings import init_settings
from badger.archive import BADGER_ARCHIVE_ROOT
from badger.errors import BadgerConfigError, BadgerLogbookError

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
    from xml.etree import ElementTree
    from re import sub

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
    try:
        log_text += f"Log location: {BADGER_LOGBOOK_ROOT}\n"
    except:
        pass

    # Generate the xml data
    curr_time = datetime.now()
    if os.name == "nt":
        timestr = curr_time.strftime("%Y-%m-%dT%H%M%S")
    else:
        timestr = curr_time.strftime("%Y-%m-%dT%H:%M:%S")
    log_entry = ElementTree.Element(None)
    severity = ElementTree.SubElement(log_entry, "severity")
    location = ElementTree.SubElement(log_entry, "location")
    keywords = ElementTree.SubElement(log_entry, "keywords")
    time = ElementTree.SubElement(log_entry, "time")
    isodate = ElementTree.SubElement(log_entry, "isodate")
    log_user = ElementTree.SubElement(log_entry, "author")
    category = ElementTree.SubElement(log_entry, "category")
    title = ElementTree.SubElement(log_entry, "title")
    metainfo = ElementTree.SubElement(log_entry, "metainfo")
    imageFile = ElementTree.SubElement(log_entry, "link")
    imageFile.text = timestr + "-00.ps"
    thumbnail = ElementTree.SubElement(log_entry, "file")
    thumbnail.text = timestr + "-00.png"
    text = ElementTree.SubElement(log_entry, "text")
    log_entry.attrib["type"] = "LOGENTRY"
    category.text = "USERLOG"
    location.text = "not set"
    severity.text = "NONE"
    keywords.text = "none"
    time.text = curr_time.strftime("%H:%M:%S")
    isodate.text = curr_time.strftime("%Y-%m-%d")
    metainfo.text = timestr + "-00.xml"
    log_user.text = " "
    title.text = "Badger"
    text.text = log_text
    if text.text == "":
        text.text = " "  # If field is truly empty, ElementTree leaves off tag entirely which causes logbook parser to fail

    fileName = os.path.join(BADGER_LOGBOOK_ROOT, metainfo.text)
    fileName = fileName.rstrip(".xml")
    xmlFile = open(fileName + ".xml", "w")
    rawString = ElementTree.tostring(log_entry, "utf-8").decode("utf-8")
    parsedString = sub(r"(?=<[^/].*>)", "\n", rawString)
    xmlString = parsedString[1:]
    xmlFile.write(xmlString)
    xmlFile.write("\n")  # Close with newline so cron job parses correctly
    xmlFile.close()
    screenshot(widget, f"{fileName}.png")


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
        # logger.warning(f'Current figure mode "{img.mode}" cannot be directly saved to .ps and will be converted to "RGB" mode')
        img = img.convert("RGB")
    # img = img.scaled(400, 600)
    name = os.path.splitext(filename)[0]
    img.save(f"{name}.ps")
