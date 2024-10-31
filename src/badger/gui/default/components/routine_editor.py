from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget, QPushButton
from PyQt5.QtWidgets import QTextEdit, QStackedWidget, QScrollArea
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QFont
from badger.gui.default.components.routine_page import BadgerRoutinePage

from badger.routine import Routine


class BadgerRoutineEditor(QWidget):
    sig_saved = pyqtSignal()
    sig_canceled = pyqtSignal()
    sig_deleted = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.init_ui()
        self.config_logic()

    def init_ui(self):
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)

        # self.seperator = seperator = QFrame()
        # seperator.setFrameShape(QFrame.HLine)
        # seperator.setFrameShadow(QFrame.Sunken)
        # seperator.setLineWidth(0)
        # seperator.setMidLineWidth(0)
        # vbox.addWidget(seperator)

        # Routine stacks
        self.stacks = stacks = QStackedWidget()

        self.routine_edit = routine_edit = QTextEdit()
        routine_edit.setReadOnly(True)
        stacks.addWidget(routine_edit)

        self.scroll_area = scroll_area = QScrollArea()
        self.routine_page = routine_page = BadgerRoutinePage()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(routine_page)
        stacks.addWidget(scroll_area)

        stacks.setCurrentIndex(1)
        vbox.addWidget(stacks)

        # Action bar
        self.action_bar = action_bar = QWidget()
        # action_bar.hide()
        hbox_action = QHBoxLayout(action_bar)
        hbox_action.setContentsMargins(8, 0, 8, 0)

        cool_font = QFont()
        cool_font.setWeight(QFont.DemiBold)
        # cool_font.setPixelSize(16)

        # Only show when create new routine
        self.btn_cancel = btn_cancel = QPushButton("Cancel")
        btn_cancel.setFixedSize(64, 32)
        btn_cancel.setFont(cool_font)
        btn_cancel.hide()

        self.btn_save = btn_save = QPushButton("Save")
        btn_save.setFixedSize(128, 32)
        btn_save.setFont(cool_font)
        hbox_action.addWidget(btn_cancel)
        hbox_action.addStretch(1)
        hbox_action.addWidget(btn_save)
        vbox.addWidget(action_bar)

    def config_logic(self):
        self.btn_cancel.clicked.connect(self.cancel_create_routine)
        self.btn_save.clicked.connect(self.save_routine)

    def set_routine(self, routine: Routine, silent=False):
        try:
            self.routine_edit.setText(routine.yaml())
        except AttributeError:
            self.routine_edit.setText("")
        self.routine_page.refresh_ui(routine, silent=silent)

    def edit_routine(self):
        self.stacks.setCurrentIndex(1)

    def cancel_create_routine(self):
        self.sig_canceled.emit()

    def save_routine(self):
        # here save() is not a property/attribute
        # it's a method that also calls _compose_routine()
        if self.routine_page.save() == 0:
            self.sig_saved.emit()

    def clear(self):
        self.routine_edit.clear()

    def switch_mode(self, mode):
        if mode == "regular":
            self.btn_cancel.hide()
        elif mode == "new routine":
            self.btn_cancel.show()
