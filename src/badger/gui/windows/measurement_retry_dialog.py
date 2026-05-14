from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase, QTextOption
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
)


class BadgerMeasurementRetryDialog(QDialog):
    def __init__(self, text="", detailedText="", parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        mainLayout = QVBoxLayout(self)

        textLabel = QLabel(
            text
            + "\n\nThere was an error setting variables or getting observables."
            + "\nRetry this measurement?"
        )
        textLabel.setMinimumWidth(320)
        textLabel.setWordWrap(True)
        font = QFont()
        font.setBold(True)
        textLabel.setFont(font)
        mainLayout.addWidget(textLabel)

        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(True)
        self.detailedTextWidget = QTextEdit(detailedText)
        self.detailedTextWidget.setReadOnly(True)
        self.detailedTextWidget.setWordWrapMode(QTextOption.NoWrap)
        monoFont = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        monoFont.setPointSize(12)
        self.detailedTextWidget.setFont(monoFont)
        scrollArea.setWidget(self.detailedTextWidget)
        mainLayout.addWidget(scrollArea)

        buttonBox = QHBoxLayout()
        self.retryButton = QPushButton("Retry Measurement")
        self.stopButton = QPushButton("Stop Run")
        self.retryButton.clicked.connect(self.accept)
        self.stopButton.clicked.connect(self.reject)
        buttonBox.addWidget(self.retryButton)
        buttonBox.addWidget(self.stopButton)
        mainLayout.addLayout(buttonBox)

        self.setWindowTitle("Measurement Error")
        self.resize(560, 360)
