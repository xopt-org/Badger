from importlib import resources
from PyQt5.QtWidgets import QHBoxLayout, QWidget, QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QSize
from badger.gui.default.windows.settings_dialog import BadgerSettingsDialog
from badger.gui.default.components.eliding_label import SimpleElidedLabel


class BadgerStatusBar(QWidget):
    def __init__(self):
        super().__init__()

        self.init_ui()
        self.config_logic()

    def init_ui(self):
        icon_ref = resources.files(__package__) / "../images/gear.png"
        with resources.as_file(icon_ref) as icon_path:
            self.icon_settings = QIcon(str(icon_path))

        hbox = QHBoxLayout(self)
        hbox.setContentsMargins(0, 0, 0, 0)

        self.summary = summary = SimpleElidedLabel()
        # summary.setStyleSheet("background-color: orange;")  # for debugging
        summary.setAlignment(Qt.AlignCenter)

        self.btn_settings = btn_settings = QPushButton()
        btn_settings.setFixedSize(24, 24)
        btn_settings.setIcon(self.icon_settings)
        btn_settings.setIconSize(QSize(12, 12))
        btn_settings.setToolTip("Badger settings")

        hbox.addWidget(summary, 1)
        hbox.addWidget(btn_settings)

    def config_logic(self):
        self.btn_settings.clicked.connect(self.go_settings)

    def set_summary(self, text):
        self.summary.setText(text)
        self.setToolTip(text)

    def go_settings(self):
        dlg = BadgerSettingsDialog(self)
        dlg.exec()
