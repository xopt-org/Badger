"""Scrollable message dialog for the Badger GUI. Displays long-form messages
with an optional expandable details section in a resizable, scrollable window,
used for showing verbose error information or optimization summaries."""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase, QPixmap, QTextOption
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
)

# from ..components.eliding_label import ElidingLabel


class BadgerScrollableMessageBox(QDialog):
    def __init__(
        self,
        icon: QPixmap | None = None,
        title: str = "Message",
        text: str = "",
        detailedText: str = "",
        parent: QDialog | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint)

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

    def setText(self, text: str) -> None:
        self.textLabel.setText(text)

    def setDetailedText(self, detailedText: str) -> None:
        self.detailedTextWidget.setText(detailedText)

    def setIcon(self, icon: QPixmap) -> None:
        # This maps the QMessageBox icons to the QDialog
        iconMap = {
            QMessageBox.Icon.Information: QMessageBox.standardIcon(
                QMessageBox.Icon.Information
            ),
            QMessageBox.Icon.Warning: QMessageBox.standardIcon(
                QMessageBox.Icon.Warning
            ),
            QMessageBox.Icon.Critical: QMessageBox.standardIcon(
                QMessageBox.Icon.Critical
            ),
            QMessageBox.Icon.Question: QMessageBox.standardIcon(
                QMessageBox.Icon.Question
            ),
        }
        standardIcon = iconMap.get(icon)
        if standardIcon:
            self.iconLabel.setPixmap(standardIcon)
