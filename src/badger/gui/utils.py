import copy
from importlib import resources
from typing import Any

from PyQt5.QtCore import QEvent, QObject, QSize, Qt
from PyQt5.QtGui import QFocusEvent, QIcon, QMouseEvent
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class MouseWheelWidgetAdjustmentGuard(QObject):
    def __init__(self, parent: QObject):
        super().__init__(parent)

    def eventFilter(self, a0: QObject, a1: QEvent) -> bool:
        # Ignore mouse wheel events for widget
        if a1.type() == QEvent.Wheel:
            a1.ignore()
            return True
        return super().eventFilter(a0, a1)


def create_button(
    icon_file: str,
    tooltip: str,
    stylesheet: str | None = None,
    size: tuple[int, int] = (32, 32),
    icon_size: tuple[int, int] | None = None,
    tool_button: bool = False,
) -> QPushButton | QToolButton:
    icon_ref = resources.files(__package__) / f"./images/{icon_file}"
    with resources.as_file(icon_ref) as icon_path:
        icon = QIcon(str(icon_path))

    btn: QPushButton | QToolButton

    if tool_button:
        btn = QToolButton()
        btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
    else:
        btn = QPushButton()

    if size:
        btn.setFixedSize(*size)
    btn.setIcon(icon)
    btn.setToolTip(tooltip)
    if icon_size:
        btn.setIconSize(QSize(*icon_size))

    if stylesheet is not None:
        btn.setStyleSheet(stylesheet)

    return btn


def filter_generator_config(name: str, config: dict[str, Any]) -> dict[str, Any]:
    filtered_config: dict[str, Any] = {}
    if name == "neldermead":
        filtered_config["adaptive"] = config["adaptive"]
    elif name == "expected_improvement":
        filtered_config["turbo_controller"] = config["turbo_controller"]
        filtered_config["numerical_optimizer"] = config["numerical_optimizer"]
        filtered_config["max_travel_distances"] = config["max_travel_distances"]
    elif name == "upper_confidence_bound":
        filtered_config["turbo_controller"] = config["turbo_controller"]
        filtered_config["numerical_optimizer"] = config["numerical_optimizer"]
        filtered_config["max_travel_distances"] = config["max_travel_distances"]
        filtered_config["beta"] = config["beta"]
    elif name == "rcds":
        filtered_config["noise"] = config["noise"]
        filtered_config["step"] = config["step"]
    elif name == "mobo":
        filtered_config["numerical_optimizer"] = config["numerical_optimizer"]
        filtered_config["max_travel_distances"] = config["max_travel_distances"]
        filtered_config["reference_point"] = config["reference_point"]
    else:
        filtered_config = config

    return copy.deepcopy(filtered_config)


class NoHoverFocusComboBox(QComboBox):
    def focusInEvent(self, event: QFocusEvent) -> None:
        # Prevent focus if it's from a hover event
        if event.reason() == Qt.MouseFocusReason:
            event.ignore()
        else:
            super().focusInEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        # Ensure the combo box behaves normally when clicked
        self.setFocus()
        super().mousePressEvent(event)

    def wheelEvent(self, event: QEvent) -> None:
        event.ignore()


class ModalOverlay(QDialog):
    def __init__(self, parent: QWidget | None = None, info: str | None = None) -> None:
        super().__init__(parent)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        if parent is not None:
            self.setGeometry(parent.geometry())

        layout = QVBoxLayout()
        if info is None:
            info = "Processing, please wait..."
        label = QLabel(info, self)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        self.setLayout(layout)
        # Semi-transparent background
        self.setStyleSheet("background-color: rgba(0, 0, 0, 80);")
