"""Error dialog that allows users to retry measurements after errors in setting variable
values / getting observables from the environment. Based on the ExpandableMessageBox dialog."""

from PyQt5.QtWidgets import QDialogButtonBox, QMessageBox

from .expandable_message_box import ExpandableMessageBox


class BadgerMeasurementRetryDialog(ExpandableMessageBox):
    def __init__(self, text="", detailedText="", parent=None):
        full_text = (
            "There was an error setting variables or getting observables.\n\n" + text
        )

        super().__init__(
            title="Measurement Error",
            text=full_text,
            detailedText=detailedText,
            parent=parent,
        )

        self.setIcon(QMessageBox.Icon.Critical)

        # Make the text big
        font = self.textLabel.font()
        font.setPointSize(12)
        self.textLabel.setFont(font)

        # So we can replace just ok button with ok+cancel buttons
        self.okButton.hide()

        self.dialogButtonBox = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        self.retryButton = self.dialogButtonBox.button(QDialogButtonBox.Ok)
        self.retryButton.setText("Retry Measurement")
        self.stopButton = self.dialogButtonBox.button(QDialogButtonBox.Cancel)
        self.stopButton.setText("Stop Run")
        self.dialogButtonBox.accepted.connect(self.accept)
        self.dialogButtonBox.rejected.connect(self.reject)

        self.buttonBox.addStretch()
        self.buttonBox.addWidget(self.dialogButtonBox)

        self.resize(560, 360)
