"""Shared Qt helpers used throughout the GUI — styled button factories,
scroll-wheel filters for spinboxes, custom combo boxes, and dialog
utilities."""

import copy
import logging
import os
from collections.abc import Callable
from functools import wraps
from importlib import resources
from typing import Any

from PyQt5.QtCore import QEvent, QObject, QSize, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QLabel,
    QPushButton,
    QToolButton,
    QVBoxLayout,
)

from badger.errors import BadgerConfigError
from badger.settings import init_settings

logger = logging.getLogger(__name__)

# Check badger optimization run archive root
config_singleton = init_settings()
BADGER_TEMP_DIRECTORY = config_singleton.read_value("BADGER_TEMP_DIRECTORY")
if BADGER_TEMP_DIRECTORY is None:
    raise BadgerConfigError("Please set the BADGER_TEMP_DIRECTORY env var!")

from PyQt5.QtGui import QFocusEvent, QMouseEvent
from PyQt5.QtWidgets import (
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


DEFAULT_ALGORITHM_RESULTS_FILE = "algorithm_results"


def build_bax_results_file(folder_id: str, create_dir: bool = False) -> str:
    """Build a ``temp/<folder-id>/algorithm_results`` prefix for BAX pkl dumps.

    ``folder_id`` should match the run's archive name (``<env>-<creation_ts>``)
    so the results directory is traceable to the archived run and stays
    consistent with what the visualizer plots. BaxGenerator does not create the
    parent directory and appends ``_<index>.pkl`` to the returned prefix, so
    ``create_dir`` should be True whenever the path is used for an actual run.
    """
    results_dir = os.path.join(BADGER_TEMP_DIRECTORY, folder_id)
    if create_dir:
        os.makedirs(results_dir, exist_ok=True)
    return os.path.join(results_dir, DEFAULT_ALGORITHM_RESULTS_FILE)


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
    elif name == "bax":
        filtered_config = config
        filtered_config["algorithm_results_file"] = (
            f"{BADGER_TEMP_DIRECTORY}{os.sep}{DEFAULT_ALGORITHM_RESULTS_FILE}"
        )

    else:
        filtered_config = config

    # Filter out all supports_* keys from the config dictionary
    filtered_config = {
        k: v for k, v in filtered_config.items() if not k.startswith("supports_")
    }

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


def set_busy_cursor() -> None:
    QApplication.setOverrideCursor(Qt.BusyCursor)


def unset_busy_cursor() -> None:
    QApplication.restoreOverrideCursor()


def with_busy_cursor(func: Callable) -> Callable:
    @wraps(func)
    def wrapped(*args, **kwargs):
        set_busy_cursor()
        try:
            return func(*args, **kwargs)
        finally:
            unset_busy_cursor()

    return wrapped
