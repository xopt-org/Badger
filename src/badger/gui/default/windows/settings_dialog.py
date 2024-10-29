from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import (
    QComboBox,
    QGridLayout,
    QVBoxLayout,
    QWidget,
    QLabel,
    QLineEdit,
)
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QApplication,
    QStyledItemDelegate,
    QCheckBox,
)
from qdarkstyle import load_stylesheet, DarkPalette, LightPalette
from badger.settings import init_settings
from badger.utils import strtobool


class BadgerSettingsDialog(QDialog):
    theme_list = ["default", "light", "dark"]
    theme_idx_dict = {
        "default": 0,
        "light": 1,
        "dark": 2,
    }

    def __init__(self, parent):
        super().__init__(parent)

        self.config_singleton = init_settings()
        self.settings = (
            self.config_singleton.list_settings()
        )  # store the current settings

        self.init_ui()
        self.config_logic()

    def init_ui(self):
        self.setWindowTitle("Badger settings")
        self.setMinimumWidth(640)

        vbox = QVBoxLayout(self)

        validator = QRegExpValidator(QRegExp(r"^[0-9]\d*(\.\d+)?$"))

        widget_settings = QWidget(self)
        grid = QGridLayout(widget_settings)
        grid.setContentsMargins(0, 0, 0, 0)

        # Theme selector
        theme = self.settings["BADGER_THEME"]["value"]
        self.lbl_theme = lbl_theme = QLabel("Theme")
        self.cb_theme = cb_theme = QComboBox()
        cb_theme.setItemDelegate(QStyledItemDelegate())
        cb_theme.addItems(self.theme_list)
        cb_theme.setCurrentIndex(self.theme_idx_dict[theme])
        grid.addWidget(lbl_theme, 0, 0)
        grid.addWidget(cb_theme, 0, 1)

        # Plugin Root
        self.plugin_root = plugin_root = QLabel("Plugin Root")
        self.plugin_root_path = plugin_root_path = QLineEdit(
            self.config_singleton.read_value("BADGER_PLUGIN_ROOT")
        )
        grid.addWidget(plugin_root, 1, 0)
        grid.addWidget(plugin_root_path, 1, 1)

        # DB Root
        self.db_root = db_root = QLabel("Database Root")
        self.db_root_path = db_root_path = QLineEdit(
            self.config_singleton.read_value("BADGER_DB_ROOT")
        )
        grid.addWidget(db_root, 2, 0)
        grid.addWidget(db_root_path, 2, 1)

        # Logbook Root
        self.logbook_root = logbook_root = QLabel("Logbook Root")
        self.logbook_root_path = logbook_root_path = QLineEdit(
            self.config_singleton.read_value("BADGER_LOGBOOK_ROOT")
        )
        grid.addWidget(logbook_root, 3, 0)
        grid.addWidget(logbook_root_path, 3, 1)

        # Archive Root
        self.archive_root = archive_root = QLabel("Archive Root")
        self.archive_root_path = archive_root_path = QLineEdit(
            self.config_singleton.read_value("BADGER_ARCHIVE_ROOT")
        )
        grid.addWidget(archive_root, 4, 0)
        grid.addWidget(archive_root_path, 4, 1)

        # Check Variable Interval
        # self.var_int = var_int = QLabel('Check Variable Interval')
        # self.var_int_val = var_int_val = QLineEdit(str(read_value('BADGER_CHECK_VAR_INTERVAL')))
        # self.var_int_val.setValidator(validator)
        # grid.addWidget(var_int, 5, 0)
        # grid.addWidget(var_int_val, 5, 1)

        # Check Variable Timeout
        # self.var_time = var_time = QLabel('Check Variable Timeout')
        # self.var_time_val = var_time_val = QLineEdit(str(read_value('BADGER_CHECK_VAR_TIMEOUT')))
        # self.var_time_val.setValidator(validator)
        # grid.addWidget(var_time, 6, 0)
        # grid.addWidget(var_time_val, 6, 1)

        # Plugin URL
        # self.plugin_url = plugin_url = QLabel('Plugin Server URL')
        # self.plugin_url_name = plugin_url_name = QLineEdit(read_value('BADGER_PLUGINS_URL'))
        # grid.addWidget(plugin_url, 7, 0)
        # grid.addWidget(plugin_url_name, 7, 1)

        # Badger data dump period
        self.dump_period = dump_period = QLabel("Data dump period")
        self.dump_period_val = dump_period_val = QLineEdit(
            str(self.config_singleton.read_value("BADGER_DATA_DUMP_PERIOD"))
        )
        self.dump_period_val.setValidator(validator)
        grid.addWidget(dump_period, 8, 0)
        grid.addWidget(dump_period_val, 8, 1)

        # Advanced settings
        self.adv_features = adv_features = QLabel("Enable Advanced Features")
        self.enable_adv_features = enable_adv_features = QCheckBox()
        enable_adv_features.setChecked(
            strtobool(self.config_singleton.read_value("BADGER_ENABLE_ADVANCED"))
        )
        grid.addWidget(adv_features, 9, 0)
        grid.addWidget(enable_adv_features, 9, 1)

        grid.setColumnStretch(1, 1)

        vbox.addWidget(widget_settings)

        self.btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)  # type: ignore

        vbox.addStretch(1)
        vbox.addWidget(self.btns)

    def config_logic(self):
        self.cb_theme.currentIndexChanged.connect(self.select_theme)
        self.btns.accepted.connect(self.apply_settings)
        self.btns.rejected.connect(self.restore_settings)

    def set_theme(self, theme):
        app = QApplication.instance()
        if theme == "dark":
            app.setStyleSheet(load_stylesheet(palette=DarkPalette))
        elif theme == "light":
            app.setStyleSheet(load_stylesheet(palette=LightPalette))
        else:
            app.setStyleSheet("")

    def select_theme(self, i):
        theme = self.theme_list[i]
        self.set_theme(theme)
        # Update the internal settings
        self.config_singleton.write_value("BADGER_THEME", theme)

    def apply_settings(self):
        self.accept()
        self.config_singleton.write_value(
            "BADGER_PLUGIN_ROOT", self.plugin_root_path.text()
        )
        self.config_singleton.write_value("BADGER_DB_ROOT", self.db_root_path.text())
        self.config_singleton.write_value(
            "BADGER_LOGBOOK_ROOT", self.logbook_root_path.text()
        )
        self.config_singleton.write_value(
            "BADGER_ARCHIVE_ROOT", self.archive_root_path.text()
        )
        # write_value('BADGER_CHECK_VAR_INTERVAL', self.var_int_val.text())
        # write_value('BADGER_CHECK_VAR_TIMEOUT', self.var_time_val.text())
        # write_value('BADGER_PLUGINS_URL', self.plugin_url_name.text())
        self.config_singleton.write_value(
            "BADGER_DATA_DUMP_PERIOD", float(self.dump_period_val.text())
        )
        self.config_singleton.write_value(
            "BADGER_ENABLE_ADVANCED", self.enable_adv_features.isChecked()
        )

    def restore_settings(self):
        # Reset theme if needed
        theme_curr = self.config_singleton.read_value("BADGER_THEME")
        theme_prev = self.settings["BADGER_THEME"]["value"]
        if theme_prev != theme_curr:
            self.set_theme(theme_prev)

        for key in self.settings.keys():
            self.config_singleton.write_value(key, self.settings[key]["value"])

        self.reject()
