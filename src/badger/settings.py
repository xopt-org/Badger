import os
import platform
import yaml
import shutil
from importlib import resources
from badger.utils import get_datadir
from pydantic import BaseModel, Field, ValidationError
from typing import Any, Dict, Optional, Union
from badger.errors import BadgerLoadConfigError
import logging
import os
import datetime

logger = logging.getLogger(__name__)


class Setting(BaseModel):
    """
    Setting model to store the configuration details.


    Attributes
    ----------
    display_name : str
        The display name of the setting.
    description : str
        A brief description of the setting.
    value : Optional[Union[str, int, bool, None]]
        The value of the setting which can be of different types.
    """

    display_name: str
    description: str
    value: Optional[Union[str, int, bool, None]] = Field(
        None, description="The value of the setting which can be of different types."
    )
    is_path: bool


class BadgerConfig(BaseModel):
    """
    BadgerConfig model to store file path, core configuration and GUI configuration details.

    Attributes
    ----------
    BADGER_PLUGIN_ROOT : Setting
        Setting for the plugin root directory.
    BADGER_TEMPLATE_ROOT : Setting
        Setting for the template root directory.
    BADGER_LOGBOOK_ROOT : Setting
        Setting for the logbook root directory.
    BADGER_ARCHIVE_ROOT : Setting
        Setting for the archive root directory.
    BADGER_LOGGING_LEVEL : Setting
        Setting for the logging level.
    BADGER_LOGFILE_PATH : Setting
        Setting for the location of logfile.
    BADGER_DATA_DUMP_PERIOD : Setting
        Setting for the minimum time interval between data dumps (in seconds).
    BADGER_THEME : Setting
        Setting for the GUI theme.
    BADGER_ENABLE_ADVANCED : Setting
        Setting to enable advanced features in the GUI.
    """

    BADGER_PLUGIN_ROOT: Setting = Setting(
        display_name="plugin root",
        description="This setting (BADGER_PLUGIN_ROOT) tells Badger where to look for the plugins",
        value=None,
        is_path=True,
    )
    BADGER_TEMPLATE_ROOT: Setting = Setting(
        display_name="template root",
        description="This setting (BADGER_TEMPLATE_ROOT) tells Badger where to store the routine templates",
        value=None,
        is_path=True,
    )
    BADGER_LOGBOOK_ROOT: Setting = Setting(
        display_name="logbook root",
        description="This setting (BADGER_LOGBOOK_ROOT) tells Badger where to send the logs (GUI mode)",
        value=None,
        is_path=True,
    )
    BADGER_ARCHIVE_ROOT: Setting = Setting(
        display_name="archive root",
        description="This setting (BADGER_ARCHIVE_ROOT) tells Badger where to archive the historical optimization runs",
        value=None,
        is_path=True,
    )
    BADGER_LOGGING_LEVEL: Setting = Setting(
        display_name="logging level",
        description="Logging level for the Badger logger",
        value="WARNING",
        is_path=False,
    )
    BADGER_LOG_DIR: Setting = Setting(
        display_name="log directory",
        description="Directory where daily log files will be stored",
        value=None,
        is_path=True,
    )
    BADGER_DATA_DUMP_PERIOD: Setting = Setting(
        display_name="data dump period",
        description="Minimum time interval between data dumps, unit is second",
        value=1,
        is_path=False,
    )
    BADGER_THEME: Setting = Setting(
        display_name="theme",
        description="Theme for the Badger GUI",
        value="dark",
        is_path=False,
    )
    BADGER_ENABLE_ADVANCED: Setting = Setting(
        display_name="enable advanced features",
        description="Enable advanced features on the GUI",
        value=False,
        is_path=False,
    )
    AUTO_REFRESH: Setting = Setting(
        display_name="Auto-refresh",
        description="Permits each run to start from the initial points calculated based on the current values and the rules",
        value=False,
        is_path=False,
    )


class ConfigSingleton:
    _instance = None
    _instance_pid = None

    def __new__(cls, config_path: str = None, user_flag: bool = False):
        current_pid = os.getpid()
        # Detect subprocess and reset singleton
        if cls._instance is not None and cls._instance_pid!=current_pid:
            logger.info(
                f"ConfigSingleton reinitializing for subprocess (PID {current_pid})"
            )
            # Clear logging handlers inherited from parent 
            root = logging.getLogger()
            root.handlers.clear()
            cls._instance = None


        if cls._instance is None:
            cls._instance = super(ConfigSingleton, cls).__new__(cls)
            cls._instance.user_flag = user_flag
            cls._instance._config = cls.load_or_create_config(config_path)
            cls._instance.config_path = config_path
        return cls._instance

    @classmethod
    def load_or_create_config(cls, config_path: str) -> BadgerConfig:
        """
        Loads the config file from a given yaml file if it exists,
        otherwise creates an instance of BadgerConfig with default settings.

        Parameters
        ----------
        config_path: str
            Path to the user config file.

        Returns
        -------
        BadgerConfig
            An instance of BadgerConfig populated with the data from the config file,
            or with default settings if the file does not exist.
        """
        if os.path.exists(config_path):
            with open(config_path, "r") as config_file:
                config_data = yaml.safe_load(config_file)

            # Convert each entry in config_data to an instance of Setting
            for key, value in config_data.items():
                if isinstance(value, dict) and "value" in value:
                    # Convert to Setting instance
                    config_data[key] = Setting(
                        display_name=value.get("display_name", key),
                        description=value.get(
                            "description",
                            f"Setting for {key.replace('_', ' ').lower()}",
                        ),
                        value=value["value"],
                        is_path=value.get("is_path", key),
                    )
                else:
                    # If it's a direct value, wrap it in a Setting
                    config_data[key] = Setting(
                        display_name=key,
                        description=f"Setting for {key.replace('_', ' ').lower()}",
                        value=value,
                        is_path=False,
                    )

            try:
                return BadgerConfig(**config_data)
            except ValidationError as e:
                print(f"Error validating config file: {e}")
                raise
        else:
            if cls._instance.user_flag:
                err_msg = f"Error loading config {config_path}: invalid path."
                raise BadgerLoadConfigError(err_msg)

            return BadgerConfig()

    @property
    def config(self) -> BadgerConfig:
        return self._config

    def update_and_save_config(self, updates: Dict[str, Any]) -> None:
        """Saves changes to the config file.

        Parameters
        ----------
        updates : dict of {str: Any}
            A dictionary containing the dot-separated keys and new values to update in the YAML file.
        """
        config_data = self._config.model_dump(by_alias=True)

        # Apply updates to the config data using dot-separated keys
        for dot_key, value in updates.items():
            self._update_config_by_dot_key(config_data, dot_key, value)

        # Save updated config to file
        with open(self.config_path, "w") as file:
            yaml.dump(config_data, file, default_flow_style=False)

        self._config = BadgerConfig(**config_data)

    def _update_config_by_dot_key(
        self, config_data: Dict[str, Any], dot_key: str, value: Any
    ) -> None:
        """Update the config data with the provided value using dot-separated keys."""
        keys = dot_key.split(":")
        d = config_data
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        last_key = keys[-1]
        if isinstance(d.get(last_key), dict) and "value" in d[last_key]:
            d[last_key]["value"] = value
        else:
            d[last_key] = value

    def list_settings(self) -> Dict[str, Any]:
        """List all the settings in Badger

        Returns
        -------
        result: Dict
            A dictionary containing the settings. Keys in the dict are fields of the
            settings, the value for each key is the current value for that setting.
        """
        return self._config.model_dump(by_alias=True)

    def list_path_settings(self) -> Dict[str, Any]:
        """List all the path-related settings in Badger

        Returns
        -------
        result: Dict
            A dictionary containing the path-related settings.
            Keys in the dict are fields of the settings,
            the value for each key is the current value for that setting.
        """
        path_dict = {}

        all_settings = self._config.model_dump(by_alias=True)
        for k, v in all_settings.items():
            if not v["is_path"]:
                continue

            # Skip the BADGER_DB_ROOT setting
            if k == "BADGER_DB_ROOT":
                continue

            path_dict[k] = v["value"]

        return path_dict

    def read_value(self, key: str, return_value_field: bool = True) -> Any:
        """
        Searches for the key in all sections of the configuration.

        Parameters
        ----------
        key: str
            The key to search for.
        return_value_field: bool
            If True, returns the 'value' field of the setting; otherwise, returns the entire setting.

        Returns
        -------
        Any
            The value associated with the provided key.

        Raises
        ------
        KeyError
            If the key is not found in the configuration.
        """
        data = self._config.model_dump(by_alias=True)
        if key in data:
            return data[key]["value"] if return_value_field else data[key]
        raise KeyError(f"Key '{key}' not found in the configuration.")

    def read_description(self, key: str, return_description_field: bool = True) -> Any:
        """
        Searches for the key in all sections of the configuration.

        Parameters
        ----------
        key: str
            The key to search for.
        return_description_field: bool
            If True, returns the 'description' field of the setting; otherwise, returns the entire setting.

        Returns
        -------
        str
            The description associated with the provided key.

        Raises
        ------
        KeyError
            If the key is not found in the configuration.
        """
        data = self._config.model_dump(by_alias=True)
        if key in data:
            return data[key]["description"] if return_description_field else data[key]
        raise KeyError(f"Key '{key}' not found in the configuration.")

    def read_display_name(
        self, key: str, return_display_name_field: bool = True
    ) -> Any:
        """
        Searches for the key in all sections of the configuration.

        Parameters
        ----------
        key: str
            The key to search for.
        return_display_name_field: bool
            If True, returns the 'display_name' field of the setting; otherwise, returns the entire setting.

        Returns
        -------
        str
            The display_name associated with the provided key.

        Raises
        ------
        KeyError
            If the key is not found in the configuration.
        """
        data = self._config.model_dump(by_alias=True)
        if key in data:
            return data[key]["display_name"] if return_display_name_field else data[key]
        raise KeyError(f"Key '{key}' not found in the configuration.")

    def read_is_path(self, key: str, return_is_path_field: bool = True) -> Any:
        """
        Searches for the key in all sections of the configuration.

        Parameters
        ----------
        key: str
            The key to search for.
        return_is_path_field: bool
            If True, returns the 'is_path' field of the setting; otherwise, returns the entire setting.

        Returns
        -------
        bool
            The is_path associated with the provided key.

        Raises
        ------
        KeyError
            If the key is not found in the configuration.
        """
        data = self._config.model_dump(by_alias=True)
        if key in data:
            return data[key]["is_path"] if return_is_path_field else data[key]
        raise KeyError(f"Key '{key}' not found in the configuration.")

    def write_value(self, key: str, value: Any) -> None:
        """A method for setting a new value to the config.

        Parameters
        ----------
        key: str
            The field that is being given a new value.
        value: Any
            The value that is being saved.
        """
        keys = key.split(".")
        updates = {}
        sub_dict = updates

        for key in keys[:-1]:
            sub_dict = sub_dict.setdefault(key, {})
        sub_dict[keys[-1]] = value

        logger.info(f"writing to config file, setting: {key} = {value}")
        self.update_and_save_config(updates)

    def reset_settings(self) -> None:
        """Resets all the settings to their default values."""
        default_config = BadgerConfig()
        self.update_and_save_config(default_config.model_dump(by_alias=True))
        print(
            f"All settings have been reset to their default values in {self.config_path}"
        )

    def get_logfile_path(self):
        """
        Get the path to today's log file in the configured log directory.
        Creates the directory if it doesn't exist.
        
        Returns:
            str: Path to today's log file (e.g., /path/to/logs/log_01_25.log)
        """
        # Get the configured log directory
        log_dir = self.read_value("BADGER_LOG_DIR")
        
        # If not set, empty, or invalid, use default (user config folder)
        if log_dir is None or log_dir == "" or log_dir == "/logs":
            from badger.settings import get_user_config_folder
            log_dir = os.path.join(get_user_config_folder(), "logs")
        
        # Expand user home directory if needed
        log_dir = os.path.expanduser(log_dir)
        
        # Make it absolute path if it's relative
        if not os.path.isabs(log_dir):
            from badger.settings import get_user_config_folder
            log_dir = os.path.join(get_user_config_folder(), log_dir)
        
        # Create directory if it doesn't exist
        try:
            os.makedirs(log_dir, exist_ok=True)
        except PermissionError:
            # Fall back to user config folder if we can't create the directory
            logger.warning(f"Cannot create log directory {log_dir}, using default")
            from badger.settings import get_user_config_folder
            log_dir = os.path.join(get_user_config_folder(), "logs")
            os.makedirs(log_dir, exist_ok=True)
        except FileExistsError:
            # Something with this name exists but it's not a directory
            logger.warning(f"{log_dir} exists but is not a directory, using default")
            from badger.settings import get_user_config_folder
            log_dir = os.path.join(get_user_config_folder(), "logs")
            os.makedirs(log_dir, exist_ok=True)
        
        # Generate today's date-based filename
        today = datetime.date.today()
        log_filename = f"log_{today.month:02d}_{today.day:02d}.log"
        
        return os.path.join(log_dir, log_filename)


def init_settings(config_arg: bool = None) -> ConfigSingleton:
    """
    Builds and returns an instance of the ConfigSingleton class.

    Parameters
    ----------
    config_arg: bool
        a path to a config file passed through the --config__filepath argument

    Returns
    -------
    config_singleton: ConfigSingleton
        an instance of the ConfigSingleton class
    """
    user_flag = False

    if config_arg is None:
        config_path = get_user_config_folder()
        file_name = "config.yaml"
        file_path = os.path.join(config_path, file_name)
    else:
        file_path = config_arg
        user_flag = True

    config_singleton = ConfigSingleton(file_path, user_flag)
    return config_singleton


def mock_settings():
    """A method for setting up mock settings"""
    config_singleton = init_settings()
    app_data_dir = get_datadir() / "Badger"
    os.makedirs(app_data_dir, exist_ok=True)

    # Configure the paths and put/refresh the mock plugins there if needed
    plugins_dir = str(app_data_dir / "plugins")
    os.makedirs(plugins_dir, exist_ok=True)
    config_singleton.write_value("BADGER_PLUGIN_ROOT", plugins_dir)
    built_in_plugins_dir = resources.files(__package__) / "built_in_plugins"
    shutil.copytree(built_in_plugins_dir, plugins_dir, dirs_exist_ok=True)

    logbook_dir = str(app_data_dir / "logbook")
    os.makedirs(logbook_dir, exist_ok=True)
    config_singleton.write_value("BADGER_LOGBOOK_ROOT", logbook_dir)

    archive_dir = str(app_data_dir / "archive")
    os.makedirs(archive_dir, exist_ok=True)
    config_singleton.write_value("BADGER_ARCHIVE_ROOT", archive_dir)

    templates_dir = str(app_data_dir / "templates")
    os.makedirs(templates_dir, exist_ok=True)
    config_singleton.write_value("BADGER_TEMPLATE_ROOT", templates_dir)

    # Set other settings to the default values
    for key in config_singleton.config.model_dump(by_alias=True).keys():
        config_singleton.write_value(
            key, config_singleton.config.model_dump(by_alias=True)[key]["value"]
        )


def get_user_config_folder() -> str:
    """
    Method for getting the path to the user specific folder on the current systems OS.

    Returns
    -------
    str
        The path to the user-specific configuration folder. This will be:
        - `%APPDATA%` or `%LOCALAPPDATA%` on Windows,
        - `~/Library/Application Support` on macOS,
        - `~/.config` on Linux.

    Raises
    ------
    OSError
        If the operating system is not supported.
    """
    system = platform.system()

    if system == "Windows":
        config_folder = os.getenv("APPDATA") or os.getenv("LOCALAPPDATA")
    elif system == "Darwin":
        config_folder = os.path.expanduser("~/Library/Application Support/Badger")
    elif system == "Linux":
        config_folder = os.path.expanduser("~/.config")
    else:
        raise OSError("Unsupported operating system")

    return config_folder
