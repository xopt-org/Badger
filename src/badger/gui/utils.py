"""Shared Qt helpers used throughout the GUI — styled button factories,
scroll-wheel filters for spinboxes, custom combo boxes, and dialog
utilities."""

import copy
import logging
import os
from datetime import datetime
from importlib import resources
from typing import Any

from PyQt5.QtCore import QEvent, QObject, QSize, Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAbstractSpinBox,
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


def preventAnnoyingSpinboxScrollBehaviour(self, control: QAbstractSpinBox) -> None:
    control.setFocusPolicy(Qt.StrongFocus)
    control.installEventFilter(self.MouseWheelWidgetAdjustmentGuard(control))


class MouseWheelWidgetAdjustmentGuard(QObject):
    def __init__(self, parent: QObject):
        super().__init__(parent)

    def eventFilter(self, o: QObject, e: QEvent) -> bool:
        # Ignore mouse wheel events for widget
        if e.type() == QEvent.Wheel:
            e.ignore()
            return True
        return super().eventFilter(o, e)


def create_button(
    icon_file,
    tooltip,
    stylesheet=None,
    size=(32, 32),
    icon_size=None,
    tool_button=False,
):
    icon_ref = resources.files(__package__) / f"./images/{icon_file}"
    with resources.as_file(icon_ref) as icon_path:
        icon = QIcon(str(icon_path))

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


def needs_new_bax_results_folder(value: str | None) -> bool:
    """Return True when the BAX results path should get a fresh per-run folder.

    A value is considered "already scoped" when it lives in its own sub-folder
    of the temp directory (``temp/<folder-id>/...``). The shared default
    (``temp/algorithm_results``) or an empty value triggers a new folder.
    """
    if not value:
        return True
    parent = os.path.dirname(value)
    return bool(os.path.normpath(parent) == os.path.normpath(BADGER_TEMP_DIRECTORY))


def build_bax_results_file(create_dir: bool = False) -> str:
    """Build a ``temp/<folder-id>/algorithm_results`` prefix for BAX pkl dumps.

    The archive name isn't known until a run starts, so the folder id is a
    timestamp. BaxGenerator does not create the parent directory and appends
    ``_<index>.pkl`` to the returned prefix, so ``create_dir`` should be True
    whenever the path is going to be used for an actual run.
    """
    folder_id = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
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

    return copy.deepcopy(filtered_config)


class NoHoverFocusComboBox(QComboBox):
    def focusInEvent(self, event):
        # Prevent focus if it's from a hover event
        if event.reason() == Qt.MouseFocusReason:
            event.ignore()
        else:
            super().focusInEvent(event)

    def mousePressEvent(self, event):
        # Ensure the combo box behaves normally when clicked
        self.setFocus()
        super().mousePressEvent(event)

    def wheelEvent(self, event):
        event.ignore()


class ModalOverlay(QDialog):
    def __init__(self, parent=None, info=None):
        super().__init__(parent)
        self.setWindowModality(Qt.ApplicationModal)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
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
