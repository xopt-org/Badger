import os
import shutil
import platform
import yaml
from importlib import resources
from PyQt5.QtCore import QSettings
from .utils import get_datadir

def load_config(self):
    """
    """
    config_path = os.path.join(self.app_support_dir, self.config_file)
        
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"{config_path} does not exist. Please create it first.")
        
    with open(config_path, 'r') as file:
        config = yaml.safe_load(file)
        
    return config

def create_config(config_file='config.yaml', template_file='config_template.yaml'):
    """
    """
    app_support_dir = get_app_support_dir()
    config_path = os.path.join(app_support_dir, config_file)
        
    if not os.path.exists(app_support_dir):
        os.makedirs(app_support_dir)

    if not os.path.exists(config_path):
        shutil.copy(template_file, config_file)
        print(f"{config_file} created from {template_file}.")
    else:
        print(f"{config_file} already exists.")

def get_app_support_dir(self):
    """
    """
    system = platform.system()
    if system == 'Darwin':  # macOS
        return os.path.expanduser('~/Library/Application Support/MyApp')
    elif system == 'Linux':  # Linux
        return os.path.expanduser('~/.config/MyApp')
    elif system == 'Windows':  # Windows
        return os.path.join(os.environ['APPDATA'], 'MyApp')
    else:
        raise ValueError(f'Unsupported OS: {system}')

def init_settings():
    config = load_config()
    settings = QSettings("SLAC-ML", "Badger")
    print(config, "WE ARE GOLDEN")
    BADGER_PATH_DICT = config["BADGER_PATH_DICT"]
    BADGER_CORE_DICT = config["BADGER_CORE_DICT"]
    BADGER_GUI_DICT = config["BADGER_GUI_DICT"]

    for key in BADGER_PATH_DICT.keys():
        if settings.value(key) is None:
            settings.setValue(key, BADGER_PATH_DICT[key]["value"])
    for key in BADGER_CORE_DICT.keys():
        if settings.value(key) is None:
            settings.setValue(key, BADGER_CORE_DICT[key]["value"])
    for key in BADGER_GUI_DICT.keys():
        if settings.value(key) is None:
            settings.setValue(key, BADGER_GUI_DICT[key]["value"])

def list_settings():
    """List all the settings in Badger

    Returns
    -------
    dict
        A dictionary contains the settings. Keys in the dict are fields of the
        settings, the value for each key is the current value for that setting.

    """
    config = load_config()
    settings = QSettings("SLAC-ML", "Badger")
    BADGER_PATH_DICT = config["BADGER_PATH_DICT"]
    BADGER_CORE_DICT = config["BADGER_CORE_DICT"]
    BADGER_GUI_DICT = config["BADGER_GUI_DICT"]

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

    config = load_config()
    settings = QSettings("SLAC-ML", "Badger")
    BADGER_CORE_DICT = config["BADGER_CORE_DICT"]
    BADGER_GUI_DICT = config["BADGER_GUI_DICT"]

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


def reset_settings():
    config = load_config()
    settings = QSettings("SLAC-ML", "Badger")
    BADGER_PATH_DICT = config["BADGER_PATH_DICT"]
    BADGER_CORE_DICT = config["BADGER_CORE_DICT"]
    BADGER_GUI_DICT = config["BADGER_GUI_DICT"]

    for key in BADGER_PATH_DICT.keys():
        settings.setValue(key, BADGER_PATH_DICT[key]["value"])
    for key in BADGER_CORE_DICT.keys():
        settings.setValue(key, BADGER_CORE_DICT[key]["value"])
    for key in BADGER_GUI_DICT.keys():
        settings.setValue(key, BADGER_GUI_DICT[key]["value"])
