import os
import shutil
import yaml
from importlib import resources
from PyQt5.QtCore import QSettings
from badger.utils import get_datadir
from badger.generate_config import generate_config
from typing import Dict, Any


BADGER_PATH_DICT = {
    "BADGER_PLUGIN_ROOT": {
        "display name": "plugin root",
        "description": "This setting (BADGER_PLUGIN_ROOT) tells Badger where to look for the plugins",
        "value": None,
    },
    "BADGER_DB_ROOT": {
        "display name": "database root",
        "description": "This setting (BADGER_DB_ROOT) tells Badger where to store the routine database",
        "value": None,
    },
    "BADGER_LOGBOOK_ROOT": {
        "display name": "logbook root",
        "description": "This setting (BADGER_LOGBOOK_ROOT) tells Badger where to send the logs (GUI mode)",
        "value": None,
    },
    "BADGER_ARCHIVE_ROOT": {
        "display name": "archive root",
        "description": "This setting (BADGER_ARCHIVE_ROOT) tells Badger where to archive the historical optimization runs",
        "value": None,
    },
}


BADGER_CORE_DICT = {
    "BADGER_DATA_DUMP_PERIOD": {
        "display name": "data dump period",
        "description": "Minimum time interval between data dumps, unit is second",
        "value": 1,
    },
}


BADGER_GUI_DICT = {
    "BADGER_THEME": {
        "display name": "theme",
        "description": "Theme for the Badger GUI",
        "value": "dark",
    },
    "BADGER_ENABLE_ADVANCED": {
        "display name": "enable advanced features",
        "description": "Enable advanced features on the GUI",
        "value": False,
    },
}


def load_config(config_dir: str, config_file: str = 'config.yaml') -> Dict:
    """
    Parameters
    ----------
    config_dir

    config_file: str 

    Returns
    -------
    config: Dict

    """
    config_path = os.path.join(config_dir, config_file)

    settings = QSettings("SLAC-ML", "Badger")
    settings.setValue("path", config_path)
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"{config_path} does not exist. Please create it first.")
        
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
    
    return config


def init_settings() -> None:
    """intialize settings for Badger. loads local config file."""
    settings = QSettings("SLAC-ML", "Badger")
    badger_dir = os.path.dirname(os.path.realpath(__file__))

    template = os.path.join(badger_dir, 'config_template.yaml')
    config = os.path.join(badger_dir, 'config.yaml')
    generate_config(template, config)

    config = load_config(badger_dir)
    
    BADGER_PATH_DICT = config["BADGER_PATH"]
    BADGER_CORE_DICT = config["BADGER_CORE"]
    BADGER_GUI_DICT = config["BADGER_GUI"]

    for key in BADGER_PATH_DICT.keys():
        if settings.value(key) is None:
            settings.setValue(key, BADGER_PATH_DICT[key]["value"])
    for key in BADGER_CORE_DICT.keys():
        if settings.value(key) is None:
            settings.setValue(key, BADGER_CORE_DICT[key]["value"])
    for key in BADGER_GUI_DICT.keys():
        if settings.value(key) is None:
            settings.setValue(key, BADGER_GUI_DICT[key]["value"])


def list_settings() -> Dict:
    """List all the settings in Badger

    Returns
    -------
    result: Dict
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


def read_value(key: str) -> Any:
    """
    Returns a value saved in the QSettings. 

    Returns
    -------
    settings.value(key): Any
        value from the QSettings dict. 
    """
    settings = QSettings("SLAC-ML", "Badger")
    return settings.value(key)


def write_value(key: str, value: Any) -> None:
    """A method for setting a new value for the Qsettings and the config file.

    Parameters
    ----------
    key: str
        The field that is having is being given a new value. 
    value: Any
        value that is being saved.
    """
    settings = QSettings("SLAC-ML", "Badger")

    settings.setValue(key, value)
    path = settings.value("path", "")
    
    update = {key: value}
    update_config_file(path, update)

def update_config_file(file_path: str, updates: Dict[str, Any]) -> None:
    """saves changes to the config file.

    Parameters
    ----------
    file_path : str
        The path to the config file to be updated.
    updates : dict of {str: Any}
        A dictionary containing the keys and new values to update in the YAML file.
    """
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
    
    for key, new_value in updates.items():
        data[key] = new_value
    
    with open(file_path, 'w') as file:
        yaml.dump(data, file, default_flow_style=False)
    

def mock_settings():
    """A method for setting up mock settings"""
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
        settings.setValue(key, BADGER_CORE_DICT[key]["value"])
    for key in BADGER_GUI_DICT.keys():
        settings.setValue(key, BADGER_GUI_DICT[key]["value"])


def reset_settings() -> None:
    """A method to reset the Qsettings in Badger"""
    settings = QSettings("SLAC-ML", "Badger")
    for key in BADGER_PATH_DICT.keys():
        settings.setValue(key, BADGER_PATH_DICT[key]["value"])
    for key in BADGER_CORE_DICT.keys():
        settings.setValue(key, BADGER_CORE_DICT[key]["value"])
    for key in BADGER_GUI_DICT.keys():
        settings.setValue(key, BADGER_GUI_DICT[key]["value"])
