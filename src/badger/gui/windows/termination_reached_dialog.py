"""Dialog shown when a run-until threshold is reached during optimization.

Lets users choose whether to continue running or end the current run,
after the run is paused by a termination condition.
"""

from typing import Any, cast

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

stylesheet_run = """
QPushButton:hover:pressed
{
    background-color: #92D38C;
}
QPushButton:hover
{
    background-color: #6EC566;
}
QPushButton
{
    background-color: #4AB640;
    color: #000000;
}
"""

stylesheet_stop = """
QPushButton:hover:pressed
{
    background-color: #C7737B;
}
QPushButton:hover
{
    background-color: #BF616A;
}
QPushButton
{
    background-color: #A9444E;
}
"""


class BadgerTerminationReachedDialog(QDialog):
    def __init__(
        self,
        tc_condition: dict[str, Any] | None = None,
        text: str = "",
        parent: QDialog | None = None,
    ) -> None:
        super().__init__(parent)

        self.setWindowTitle("Termination Condition Reached")
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        tc_condition = cast(dict[str, Any], tc_condition)
        tc_type = tc_condition["type"]
        if tc_type == "max_eval":
            tc_type_text = "N iterations"
            state = tc_condition["state"]
        else:
            tc_type_text = "Timeout"
            state = f"{tc_condition['state']:.2f} s"

        content_row = QHBoxLayout()
        content_row.setSpacing(6)

        text_column = QVBoxLayout()
        text_column.setSpacing(3)

        summary_label = QLabel(f"{tc_type_text}: {state} / {tc_condition['config']}")
        summary_label.setWordWrap(True)
        # PyQt5 stubs type flag OR as int, so cast back to the flag type.
        summary_label.setAlignment(
            cast(
                Qt.AlignmentFlag,
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            )
        )
        #  summary_label.setStyleSheet("color: #8A949E;")
        text_column.addWidget(summary_label)

        body_label = QLabel("Badger optimization paused")
        body_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        text_column.addWidget(body_label)

        content_row.addLayout(text_column)
        layout.addLayout(content_row)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.continueButton = button_box.button(QDialogButtonBox.Ok)
        self.endButton = button_box.button(QDialogButtonBox.Cancel)

        font = self.font()
        font.setPointSize(12)
        self.setFont(font)

        if self.continueButton is not None:
            self.continueButton.setText("Continue")
            # self.continueButton.setStyleSheet(stylesheet_run)
            self.continueButton.setFixedSize(96, 24)
        if self.endButton is not None:
            self.endButton.setText("End Run")
            self.endButton.setStyleSheet(stylesheet_stop)
            self.endButton.setFixedSize(96, 24)

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.resize(360, 150)
