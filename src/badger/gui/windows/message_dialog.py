from PyQt5.QtWidgets import (
    QDialog,
    QMessageBox,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTextEdit,
)
from PyQt5.QtGui import QTextOption, QFont, QFontDatabase
# from ..components.eliding_label import ElidingLabel


class BadgerScrollableMessageBox(QDialog):
    def __init__(
        self, icon=None, title="Message", text="", detailedText="", parent=None
    ):
        super().__init__(parent)

        # Main layout
        mainLayout = QVBoxLayout(self)

        # Top layout for icon and main text
        topLayout = QHBoxLayout()
        self.iconLabel = QLabel()
        if icon:
            self.iconLabel.setPixmap(icon.pixmap(64, 64))
        self.textLabel = QLabel(text)
        self.textLabel.setMinimumWidth(280)
        self.textLabel.setWordWrap(True)
        font = QFont()
        font.setBold(True)
        self.textLabel.setFont(font)
        topLayout.addWidget(self.iconLabel)
        topLayout.addWidget(self.textLabel, 1)
        mainLayout.addLayout(topLayout)

        # Scroll area for detailed text
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.detailedTextWidget = QTextEdit(detailedText)
        self.detailedTextWidget.setReadOnly(True)
        self.detailedTextWidget.setWordWrapMode(QTextOption.NoWrap)
        monoFont = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        monoFont.setPointSize(12)
        self.detailedTextWidget.setFont(monoFont)
        self.scrollArea.setWidget(self.detailedTextWidget)
        mainLayout.addWidget(self.scrollArea)

        # Buttons
        self.buttonBox = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.buttonBox.addWidget(self.okButton)
        mainLayout.addLayout(self.buttonBox)

        # Set window properties
        self.setWindowTitle(title)
        self.resize(420, 300)

    def setText(self, text):
        self.textLabel.setText(text)

    def setDetailedText(self, detailedText):
        self.detailedTextWidget.setText(detailedText)

    def setIcon(self, icon):
        # This maps the QMessageBox icons to the QDialog
        iconMap = {
            QMessageBox.Information: QMessageBox.standardIcon(QMessageBox.Information),
            QMessageBox.Warning: QMessageBox.standardIcon(QMessageBox.Warning),
            QMessageBox.Critical: QMessageBox.standardIcon(QMessageBox.Critical),
            QMessageBox.Question: QMessageBox.standardIcon(QMessageBox.Question),
        }
        standardIcon = iconMap.get(icon)
        if standardIcon:
            self.iconLabel.setPixmap(standardIcon)
