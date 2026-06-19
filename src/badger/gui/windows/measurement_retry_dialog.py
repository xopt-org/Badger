"""Dialog shown when setting variables or reading observables fails mid-run.
Displays the error (with an expandable details pane) and asks the user whether
to retry the measurement or stop the run."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase, QTextOption
from PyQt5.QtWidgets import (
    QDialog,
    QLabel,
    QDialogButtonBox,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
)


class BadgerMeasurementRetryDialog(QDialog):
    def __init__(self, text="", detailedText="", parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        mainLayout = QVBoxLayout(self)

        self.textLabel = QLabel(
            text
            + "\n\nThere was an error setting variables or getting observables."
            + "\nRetry this measurement?"
        )
        self.textLabel.setMinimumWidth(320)
        self.textLabel.setWordWrap(True)
        font = QFont()
        font.setBold(True)
        self.textLabel.setFont(font)
        mainLayout.addWidget(self.textLabel)

        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(True)
        self.detailedTextWidget = QTextEdit(detailedText)
        self.detailedTextWidget.setReadOnly(True)
        self.detailedTextWidget.setWordWrapMode(QTextOption.WrapAnywhere)
        monoFont = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        monoFont.setPointSize(12)
        self.detailedTextWidget.setFont(monoFont)
        scrollArea.setWidget(self.detailedTextWidget)
        mainLayout.addWidget(scrollArea)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.retryButton = self.buttonBox.button(QDialogButtonBox.Ok)
        self.retryButton.setText("Retry Measurement")
        self.stopButton = self.buttonBox.button(QDialogButtonBox.Cancel)
        self.stopButton.setText("Stop Run")
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        mainLayout.addWidget(self.buttonBox)

        self.setWindowTitle("Measurement Error")
        self.resize(560, 360)
