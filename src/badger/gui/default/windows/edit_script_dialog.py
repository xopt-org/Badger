from PyQt5.QtWidgets import QDialog, QPlainTextEdit, QVBoxLayout, QWidget
from PyQt5.QtWidgets import QHBoxLayout, QPushButton
from PyQt5.QtGui import QFont
from badger.gui.default.components.syntax import PythonHighlighter


class BadgerEditScriptDialog(QDialog):
    def __init__(self, parent, generator, script, callback):
        super().__init__(parent)

        self.generator = generator
        self.script = script
        self.callback = callback

        self.init_ui()
        self.config_logic()

    def init_ui(self):
        self.setWindowTitle(f"Edit Script for {self.generator}")
        self.resize(640, 640)

        vbox = QVBoxLayout(self)

        self.script_editor = script_editor = QPlainTextEdit()
        self.highlighter = PythonHighlighter(script_editor.document())
        font = QFont("Menlo", 13)
        font.setFixedPitch(True)
        script_editor.setFont(font)
        script_editor.setPlainText(self.script)

        # Button set
        button_set = QWidget()
        hbox_set = QHBoxLayout(button_set)
        hbox_set.setContentsMargins(0, 0, 0, 0)
        self.btn_cancel = btn_cancel = QPushButton("Cancel")
        self.btn_save = btn_save = QPushButton("Save")
        btn_save.setDisabled(True)
        btn_cancel.setFixedSize(96, 24)
        btn_save.setFixedSize(96, 24)
        hbox_set.addStretch()
        hbox_set.addWidget(btn_cancel)
        hbox_set.addWidget(btn_save)

        vbox.addWidget(script_editor)
        vbox.addWidget(button_set)

    def config_logic(self):
        self.script_editor.textChanged.connect(self.text_changed)
        self.btn_cancel.clicked.connect(self.cancel_changes)
        self.btn_save.clicked.connect(self.save_changes)

    def text_changed(self):
        self.btn_save.setDisabled(False)

    def cancel_changes(self):
        self.callback(self.script)
        self.accept()

    def save_changes(self):
        self.callback(self.script_editor.toPlainText())
        self.accept()
