from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QTextBrowser, QVBoxLayout

from badger.routine import Routine
from badger.utils import get_yaml_string


class BadgerReviewDialog(QDialog):
    def __init__(self, parent, routine: Routine):
        super().__init__(parent)

        self.routine = routine

        self.init_ui()
        self.config_logic()

    def init_ui(self):
        name = self.routine.name
        self.setWindowTitle(f"Review routine {name}")

        vbox = QVBoxLayout(self)

        brow_routine = QTextBrowser()
        brow_routine.setText(get_yaml_string(self.routine))

        self.btn_ok = btn_ok = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)

        vbox.addWidget(brow_routine)
        vbox.addWidget(btn_ok)

    def config_logic(self):
        self.btn_ok.accepted.connect(self.accept)
