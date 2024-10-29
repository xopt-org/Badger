import os
import platform
import pytest
import yaml
from unittest.mock import patch, MagicMock, mock_open
from badger.settings import (
    init_settings,
    get_user_config_folder,
    ConfigSingleton,
    BadgerConfig,
    Setting,
)


class TestBadgerConfig:
    config_file = "/mock/config.yaml"

    def setup_method(self, method):
        self.mock_badger_config = BadgerConfig(
            BADGER_PLUGIN_ROOT=Setting(
                display_name="plugin root",
                description="Mock plugin root",
                value="/mock/plugin/root",
                is_path=True,
            ),
            BADGER_DB_ROOT=Setting(
                display_name="database root",
                description="Mock database root",
                value="/mock/db/root",
                is_path=True,
            ),
            BADGER_LOGBOOK_ROOT=Setting(
                display_name="logbook root",
                description="Mock logbook root",
                value="/mock/logbook/root",
                is_path=True,
            ),
            BADGER_ARCHIVE_ROOT=Setting(
                display_name="archive root",
                description="Mock archive root",
                value="/mock/archive/root",
                is_path=True,
            ),
            BADGER_DATA_DUMP_PERIOD=Setting(
                display_name="data dump period",
                description="Mock data dump period",
                value=5,
                is_path=False,
            ),
            BADGER_THEME=Setting(
                display_name="theme",
                description="Mock theme",
                value="light",
                is_path=False,
            ),
            BADGER_ENABLE_ADVANCED=Setting(
                display_name="enable advanced",
                description="Mock enable advanced",
                value=True,
                is_path=False,
            ),
        )

    def teardown_method(self, method):
        ConfigSingleton._instance = None
        self.mock_badger_config = None

    def test_get_user_config_folder_windows(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Windows")
        monkeypatch.setenv("APPDATA", r"C:\Users\test\AppData\Roaming")

        config_folder = get_user_config_folder()

        assert config_folder == r"C:\Users\test\AppData\Roaming"

    def test_get_user_config_folder_mac(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Darwin")
        monkeypatch.setattr(
            os.path,
            "expanduser",
            lambda x: "/Users/test/Library/Application Support/Badger",
        )

        config_folder = get_user_config_folder()

        assert config_folder == "/Users/test/Library/Application Support/Badger"

    def test_get_user_config_folder_linux(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        monkeypatch.setattr(os.path, "expanduser", lambda x: "/home/test/.config")

        config_folder = get_user_config_folder()

        assert config_folder == "/home/test/.config"

    def test_get_user_config_folder_unsupported_os(self, monkeypatch):
        monkeypatch.setattr(platform, "system", lambda: "UnsupportedOS")

        with pytest.raises(OSError):
            get_user_config_folder()

    def test_init_settings(self):
        mock_config_singleton = MagicMock(spec=ConfigSingleton)
        with patch(
            "badger.settings.get_user_config_folder", return_value="/mock/config/folder"
        ):
            with patch(
                "badger.settings.ConfigSingleton", return_value=mock_config_singleton
            ) as mock_config_cls:
                config_singleton = init_settings()
                mock_config_cls.assert_called_once_with(
                    "/mock/config/folder/config.yaml"
                )
                assert config_singleton == mock_config_singleton

    def test_config_singleton_initialization(self):
        # Patch the open function and ensure it reads the correct mock configuration
        with patch("os.path.exists", return_value=True):
            with patch(
                "builtins.open",
                mock_open(
                    read_data=yaml.dump(self.mock_badger_config.dict(by_alias=True))
                ),
            ):
                config_singleton = ConfigSingleton(self.config_file)
                assert (
                    config_singleton.config.BADGER_PLUGIN_ROOT.value
                    == "/mock/plugin/root"
                )
                assert config_singleton.config.BADGER_DB_ROOT.value == "/mock/db/root"

    def test_config_singleton_create_new_config_if_not_exists(self):
        with patch("os.path.exists", return_value=False):
            with patch(
                "badger.settings.BadgerConfig", return_value=self.mock_badger_config
            ):
                config_singleton = ConfigSingleton(self.config_file)
                assert isinstance(config_singleton.config, BadgerConfig)

    def test_update_and_save_config(self):
        with patch("os.path.exists", return_value=True):
            with patch(
                "builtins.open",
                mock_open(
                    read_data=yaml.dump(self.mock_badger_config.dict(by_alias=True))
                ),
            ):
                config_singleton = ConfigSingleton(self.config_file)
                updates = {"BADGER_PLUGIN_ROOT": "/new/plugin/root"}
                config_singleton.update_and_save_config(updates)
                assert (
                    config_singleton.config.BADGER_PLUGIN_ROOT.value
                    == "/new/plugin/root"
                )

    def test_list_settings(self):
        with patch("os.path.exists", return_value=True):
            with patch(
                "builtins.open",
                mock_open(
                    read_data=yaml.dump(self.mock_badger_config.dict(by_alias=True))
                ),
            ):
                config_singleton = ConfigSingleton(self.config_file)
                settings = config_singleton.list_settings()
                assert "BADGER_PLUGIN_ROOT" in settings
                assert settings["BADGER_PLUGIN_ROOT"]["value"] == "/mock/plugin/root"

    def test_read_value(self):
        with patch("os.path.exists", return_value=True):
            with patch(
                "builtins.open",
                mock_open(
                    read_data=yaml.dump(self.mock_badger_config.dict(by_alias=True))
                ),
            ):
                config_singleton = ConfigSingleton(self.config_file)
                value = config_singleton.read_value("BADGER_PLUGIN_ROOT")
                assert value == "/mock/plugin/root"

    def test_read_display_name(self):
        with patch("os.path.exists", return_value=True):
            with patch(
                "builtins.open",
                mock_open(
                    read_data=yaml.dump(self.mock_badger_config.dict(by_alias=True))
                ),
            ):
                config_singleton = ConfigSingleton(self.config_file)
                display_name = config_singleton.read_display_name("BADGER_PLUGIN_ROOT")
                assert display_name == "plugin root"

    def test_read_description(self):
        with patch("os.path.exists", return_value=True):
            with patch(
                "builtins.open",
                mock_open(
                    read_data=yaml.dump(self.mock_badger_config.dict(by_alias=True))
                ),
            ):
                config_singleton = ConfigSingleton(self.config_file)
                description = config_singleton.read_description("BADGER_PLUGIN_ROOT")
                assert description == "Mock plugin root"

    def test_read_is_path(self):
        with patch("os.path.exists", return_value=True):
            with patch(
                "builtins.open",
                mock_open(
                    read_data=yaml.dump(self.mock_badger_config.dict(by_alias=True))
                ),
            ):
                config_singleton = ConfigSingleton(self.config_file)
                is_path = config_singleton.read_is_path("BADGER_PLUGIN_ROOT")
                assert is_path

    def test_write_value(self):
        with patch("os.path.exists", return_value=True):
            with patch(
                "builtins.open",
                mock_open(
                    read_data=yaml.dump(self.mock_badger_config.dict(by_alias=True))
                ),
            ):
                config_singleton = ConfigSingleton(self.config_file)
                config_singleton.write_value("BADGER_PLUGIN_ROOT", "/new/plugin/root")
                assert (
                    config_singleton.config.BADGER_PLUGIN_ROOT.value
                    == "/new/plugin/root"
                )

    def test_reset_settings(self):
        with patch("os.path.exists", return_value=False):
            with patch(
                "badger.settings.BadgerConfig", return_value=self.mock_badger_config
            ):
                config_singleton = ConfigSingleton(self.config_file)
                with patch.object(
                    config_singleton, "update_and_save_config"
                ) as mock_update:
                    config_singleton.reset_settings()
                    assert mock_update.called
                    assert isinstance(config_singleton.config, BadgerConfig)

    # TODO: Missing test for mock_settings method
