import os
import shutil
from importlib import resources
from PyQt5.QtCore import QSettings
from .utils import get_datadir


BADGER_PATH_DICT = {
    "BADGER_PLUGIN_ROOT": {
        "display name": "plugin root",
        "description": "This setting (BADGER_PLUGIN_ROOT) tells Badger where to look for the plugins",
        "default value": None,
    },
    "BADGER_DB_ROOT": {
        "display name": "database root",
        "description": "This setting (BADGER_DB_ROOT) tells Badger where to store the routine database",
        "default value": None,
    },
    "BADGER_LOGBOOK_ROOT": {
        "display name": "logbook root",
        "description": "This setting (BADGER_LOGBOOK_ROOT) tells Badger where to send the logs (GUI mode)",
        "default value": None,
    },
    "BADGER_ARCHIVE_ROOT": {
        "display name": "archive root",
        "description": "This setting (BADGER_ARCHIVE_ROOT) tells Badger where to archive the historical optimization runs",
        "default value": None,
    },
}


BADGER_CORE_DICT = {
    # 'BADGER_CHECK_VAR_INTERVAL': {
    #     'display name': 'check var interval',
    #     'description': 'Waiting time between each round of check var when set var to env, unit is second',
    #     'default value': 0.1,
    # },
    # 'BADGER_CHECK_VAR_TIMEOUT': {
    #     'display name': 'check var timeout',
    #     'description': 'Maximum waiting time before giving up check var if takes too long time, unit is second',
    #     'default value': 3,
    # },
    "BADGER_DATA_DUMP_PERIOD": {
        "display name": "data dump period",
        "description": "Minimum time interval between data dumps, unit is second",
        "default value": 1,
    },
    # 'BADGER_PLUGINS_URL': {
    #     'display name': 'badger plugins url',
    #     'description': 'URL for badger plugins server',
    #     'default value': 'http://teeport.ml/badger-plugins'
    # }
}


BADGER_GUI_DICT = {
    "BADGER_THEME": {
        "display name": "theme",
        "description": "Theme for the Badger GUI",
        "default value": "dark",
    },
    "BADGER_ENABLE_ADVANCED": {
        "display name": "enable advanced features",
        "description": "Enable advanced features on the GUI",
        "default value": False,
    },
}


def init_settings():
    settings = QSettings("SLAC-ML", "Badger")

    for key in BADGER_PATH_DICT.keys():
        if settings.value(key) is None:
            settings.setValue(key, BADGER_PATH_DICT[key]["default value"])
    for key in BADGER_CORE_DICT.keys():
        if settings.value(key) is None:
            settings.setValue(key, BADGER_CORE_DICT[key]["default value"])
    for key in BADGER_GUI_DICT.keys():
        if settings.value(key) is None:
            settings.setValue(key, BADGER_GUI_DICT[key]["default value"])


def list_settings():
    """List all the settings in Badger

    Returns
    -------
    dict
        A dictionary contains the settings. Keys in the dict are fields of the
        settings, the value for each key is the current value for that setting.

    """
    settings = QSettings("SLAC-ML", "Badger")
    result = {}
    for key in BADGER_PATH_DICT.keys():
        result[key] = settings.value(key)
    for key in BADGER_CORE_DICT.keys():
        result[key] = settings.value(key)
    for key in BADGER_GUI_DICT.keys():
        result[key] = settings.value(key)

    return result


def read_value(key):
    settings = QSettings("SLAC-ML", "Badger")

    return settings.value(key)


def write_value(key, value):
    settings = QSettings("SLAC-ML", "Badger")

    settings.setValue(key, value)


def mock_settings():
    app_data_dir = get_datadir() / "Badger"
    os.makedirs(app_data_dir, exist_ok=True)

    settings = QSettings("SLAC-ML", "Badger")

    # Configure the paths and put/refresh the mock plugins there if needed
    plugins_dir = str(app_data_dir / "plugins")
    os.makedirs(plugins_dir, exist_ok=True)
    settings.setValue("BADGER_PLUGIN_ROOT", plugins_dir)
    built_in_plugins_dir = resources.files(__package__) / "built_in_plugins"
    shutil.copytree(built_in_plugins_dir, plugins_dir, dirs_exist_ok=True)

    db_dir = str(app_data_dir / "db")
    os.makedirs(db_dir, exist_ok=True)
    settings.setValue("BADGER_DB_ROOT", db_dir)

    logbook_dir = str(app_data_dir / "logbook")
    os.makedirs(logbook_dir, exist_ok=True)
    settings.setValue("BADGER_LOGBOOK_ROOT", logbook_dir)

    archive_dir = str(app_data_dir / "archive")
    os.makedirs(archive_dir, exist_ok=True)
    settings.setValue("BADGER_ARCHIVE_ROOT", archive_dir)

    # Set other settings to the default values
    for key in BADGER_CORE_DICT.keys():
        settings.setValue(key, BADGER_CORE_DICT[key]["default value"])
    for key in BADGER_GUI_DICT.keys():
        settings.setValue(key, BADGER_GUI_DICT[key]["default value"])


def reset_settings():
    settings = QSettings("SLAC-ML", "Badger")
    for key in BADGER_PATH_DICT.keys():
        settings.setValue(key, BADGER_PATH_DICT[key]["default value"])
    for key in BADGER_CORE_DICT.keys():
        settings.setValue(key, BADGER_CORE_DICT[key]["default value"])
    for key in BADGER_GUI_DICT.keys():
        settings.setValue(key, BADGER_GUI_DICT[key]["default value"])
