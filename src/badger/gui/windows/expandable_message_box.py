from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QFontDatabase, QTextOption
from PyQt5.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)


class ExpandableMessageBox(QDialog):
    def __init__(
        self,
        icon: QMessageBox.Icon | None = None,
        title: str = "Message",
        text: str = "",
        detailedText: str = "",
        parent: QDialog | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

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

        # Detailed text area setup
        self.detailedTextWidget = QTextEdit()
        self.detailedTextWidget.setText(detailedText)
        self.detailedTextWidget.setReadOnly(True)
        self.detailedTextWidget.setWordWrapMode(
            QTextOption.WrapAtWordBoundaryOrAnywhere
        )
        monoFont = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        monoFont.setPointSize(9)
        self.detailedTextWidget.setFont(monoFont)
        self.detailedTextWidget.setVisible(False)  # Initially hidden

        # Button to show/hide details
        self.toggleButton = QPushButton("Show Details")
        self.toggleButton.clicked.connect(self.toggle_details)

        # Layouts for the detailed text and button
        self.detailLayout = QVBoxLayout()
        self.detailLayout.addWidget(self.detailedTextWidget)
        self.detailLayout.addWidget(self.toggleButton)

        # Add the detailed text area and toggle button to the main layout
        mainLayout.addLayout(self.detailLayout)

        # Buttons
        self.buttonBox = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.buttonBox.addWidget(self.okButton)
        mainLayout.addLayout(self.buttonBox)

        # Set window properties
        self.setWindowTitle(title)
        self.resize(420, 250)

    def toggle_details(self) -> None:
        if self.detailedTextWidget.isVisible():
            self.detailedTextWidget.setVisible(False)
            self.toggleButton.setText("Show Details")
        else:
            self.detailedTextWidget.setVisible(True)
            self.toggleButton.setText("Hide Details")

    def setText(self, text: str) -> None:
        self.textLabel.setText(text)

    def setDetailedText(self, detailedText: str) -> None:
        self.detailedTextWidget.setText(detailedText)

    def setIcon(self, icon: QMessageBox.Icon) -> None:
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
