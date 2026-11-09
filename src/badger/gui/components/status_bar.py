"""Bottom status bar showing run status and a settings button."""

from importlib import resources

from PyQt5.QtCore import QSize, Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QHBoxLayout, QPushButton, QWidget

from badger.gui.components.eliding_label import SimpleElidedLabel
from badger.gui.windows.settings_dialog import BadgerSettingsDialog


class BadgerStatusBar(QWidget):
    sig_edit_termination_condition = pyqtSignal()

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
        self.bg = QWidget()
        hbox.addWidget(self.bg, 1)
        self.bg.setObjectName("StatusBar")
        hbox_bg = QHBoxLayout(self.bg)
        hbox_bg.setContentsMargins(2, 2, 2, 2)

        self.summary = summary = SimpleElidedLabel()
        summary.setObjectName("StatusBar")
        # summary.setStyleSheet("background-color: orange;")  # for debugging
        summary.setAlignment(Qt.AlignCenter)

        self.btn_termination = btn_termination = QPushButton()
        btn_termination.setObjectName("TerminationCondition")
        btn_termination.setFixedHeight(24)
        btn_termination.setToolTip("Edit termination condition")

        self.btn_settings = btn_settings = QPushButton()
        btn_settings.setObjectName("Settings")
        btn_settings.setStyleSheet("background-color: transparent; border: none;")
        btn_settings.setFixedSize(24, 24)
        btn_settings.setIcon(self.icon_settings)
        btn_settings.setIconSize(QSize(12, 12))
        btn_settings.setToolTip("Badger settings")

        self.left_controls = QWidget()
        self.left_controls.setObjectName("Controls")
        left_layout = QHBoxLayout(self.left_controls)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)
        left_layout.addWidget(btn_termination, 0, Qt.AlignLeft)

        self.right_controls = QWidget()
        self.right_controls.setObjectName("Controls")
        right_layout = QHBoxLayout(self.right_controls)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addStretch(1)
        right_layout.addWidget(btn_settings, 0, Qt.AlignRight)

        hbox_bg.setSpacing(0)
        hbox_bg.addWidget(self.left_controls)
        hbox_bg.addWidget(summary, 1)
        hbox_bg.addWidget(self.right_controls)

        self.setStyleSheet("""
            #StatusBar {
                background-color: #262E38;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }
            QWidget#Controls {
                background-color: #262E38;
            }
            QPushButton#TerminationCondition {
                background-color: #262E38;
                border: 1px solid #8F7740;
                border-radius: 4px;
                padding: 1px 8px;
                font-size: 12px;
            }
            QPushButton#TerminationCondition:hover {
                border-color: #C6A85A;
            }
            QPushButton#TerminationCondition:focus {
                border: 2px solid #E5C66C;
            }
        """)
        self.set_termination_condition(None)

    def config_logic(self):
        self.btn_settings.clicked.connect(self.go_settings)
        self.btn_termination.clicked.connect(self.sig_edit_termination_condition.emit)

    def set_summary(self, text):
        self.summary.setText(text)
        self.setToolTip(text)

    def set_termination_condition(self, condition):
        if condition is None:
            text = "Run until: not set"
        elif condition.get("tc_idx") == 0:
            text = f"Run until: +{condition.get('max_eval', '')} iterations"
        elif condition.get("tc_idx") == 1:
            text = f"Run until: +{int(condition.get('max_time', 0))} seconds"
        else:
            text = "Run until: "

        self.btn_termination.setText(text)
        side_width = max(
            self.btn_termination.sizeHint().width(), self.btn_settings.width()
        )
        self.left_controls.setFixedWidth(side_width)
        self.right_controls.setFixedWidth(side_width)

    def go_settings(self):
        dlg = BadgerSettingsDialog(self)
        dlg.exec()
