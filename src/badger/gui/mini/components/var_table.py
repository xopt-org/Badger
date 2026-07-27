"""
Variable table widget for the Badger mini GUI.

Provides class VariableTable, a PyQt5.QtWidgets.QTableWidget
subclass that displays optimizer variables with their saved values,
current values, and adjustable scan ranges.  Also defines the supporting
ui cell widgets (SavedValueCell, CurrentValueCell, ScanRangeCell) and the
RangeAdjustButtonStack helper.
"""

from functools import partial
from importlib import resources
import math
import traceback
from typing import Any, cast
from PyQt5.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCheckBox,
    QMessageBox,
    QAbstractItemView,
    QPushButton,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QMenu,
    QGridLayout,
    QLabel,
    QDialog,
)
from PyQt5.QtCore import pyqtSignal, Qt, QSize, QPoint, QTimer
from PyQt5.QtGui import (
    QColor,
    QIcon,
    QGuiApplication,
    QDropEvent,
    QDragMoveEvent,
    QDragEnterEvent,
)

from badger.environment import Environment, instantiate_env
from badger.errors import BadgerInterfaceChannelError
from badger.gui.windows.expandable_message_box import ExpandableMessageBox
from badger.utils import _round_bounds_inward

from gest_api.vocs import ContinuousVariable

import logging

logger = logging.getLogger(__name__)


class ValueCell(QWidget):
    """
    UI table element parent class for displaying variable values
    """

    UNSELECTED_COLOR = "gray"
    ALERT_COLOR = "#EE982F"

    def __init__(self, value: float | None):
        super().__init__()
        self.setAutoFillBackground(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)

        self.label = QLabel(self._format(value))
        self.label.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        layout.addWidget(self.label)

    @staticmethod
    def _format(value: float | None) -> str:
        if value is None:
            return "N/A"
        return f"{value:.4f}"

    def update_style(
        self,
        is_selected: bool,
        alert_level: int,
        selected_color: str,
    ):
        """
        Update the value cell visual style.

        Parameters
        ----------
        is_selected : bool
            Whether the parent row is selected.
        alert_level : int
            Alert severity, 0 is no alert, severity increases with higher integers
        selected_color : str
            Text color to use for is_selected

        Notes
        -----
        The current code path always passes 0 for alert_level. This
        behavior can be modified in the future if desired.
        """
        label_color = selected_color if is_selected else self.UNSELECTED_COLOR
        if alert_level == 1:
            label_color = self.ALERT_COLOR
        self.label.setStyleSheet(
            f"color: {label_color}; background-color: transparent; border: none;"
        )
        border = "1px solid red" if alert_level == 2 else "1px solid transparent"
        self.setStyleSheet(
            f"background-color: transparent; border: {border}; border-radius: 2px;"
        )

    def set_value(self, value: float | None) -> None:
        self.label.setText(self._format(value))


class SavedValueCell(ValueCell):
    """
    UI table element for displaying saved variable values
    """

    SELECTED_COLOR = "#AAAAAA"

    def __init__(self, value: float | None):
        super().__init__(value)

    def update_style(self, is_selected: bool, alert_level: int):
        super().update_style(
            is_selected, 0 if alert_level <= 1 else 2, self.SELECTED_COLOR
        )


class CurrentValueCell(ValueCell):
    """
    UI table element for displaying current variable values
    """

    SELECTED_COLOR = "lightgray"

    def __init__(self, value: float | None):
        super().__init__(value)

    def update_style(self, is_selected: bool, alert_level: int):
        super().update_style(is_selected, alert_level, self.SELECTED_COLOR)


class RangeAdjustButtonStack(QWidget):
    """Compact up/down buttons for range adjustments."""

    BUTTON_STYLE = """
        QPushButton {
            border: 1px solid #4A5666;
            border-radius: 1px;
            background: transparent;
            color: #C4CCD4;
            font-size: 7px;
            padding: 0;
        }
        QPushButton:hover {
            background: rgba(255, 255, 255, 0.1);
        }
        QPushButton:pressed {
            background: rgba(255, 255, 255, 0.2);
        }
    """

    def __init__(
        self,
        on_increase=None,
        on_decrease=None,
        parent: QWidget | None = None,
        button_size: QSize = QSize(12, 10),
    ):
        super().__init__(parent)

        self.up_btn = QPushButton("▲")
        self.down_btn = QPushButton("▼")

        for btn in (self.up_btn, self.down_btn):
            btn.setFixedSize(button_size)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setStyleSheet(self.BUTTON_STYLE)
            btn.setToolTip("Scale range by 1.111 (up) / 0.9 (down)")

        if on_increase is not None:
            self.up_btn.clicked.connect(on_increase)
        if on_decrease is not None:
            self.down_btn.clicked.connect(on_decrease)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.up_btn)
        layout.addWidget(self.down_btn)


class ScanRangeCell(QWidget):
    """
    UI table element to display and adjust scan range delta
    """

    UNSELECTED_COLOR = "gray"
    SELECTED_COLOR = "lightgray"

    sig_increase = pyqtSignal()
    sig_decrease = pyqtSignal()

    @staticmethod
    def _is_centered(value: float, lower: float, upper: float) -> bool:
        midpoint = 0.5 * (lower + upper)
        return math.isclose(value, midpoint, rel_tol=1e-6, abs_tol=1e-9)

    def __init__(
        self,
        value: float,
        bounds: tuple[float, float] | list[float] | ContinuousVariable,
        is_clipped: bool = False,
    ):
        super().__init__()

        if isinstance(bounds, ContinuousVariable):
            lower, upper = bounds.domain
        else:
            lower, upper = bounds

        delta = 0.5 * abs(upper - lower)
        is_centered = self._is_centered(value, lower, upper)

        if is_clipped:
            lower_delta = abs(value - lower)
            upper_delta = abs(upper - value)
            delta = max(lower_delta, upper_delta)

        self.line_edit = QLineEdit(
            f"±{delta:.3f}{'*' if is_clipped or not is_centered else ''}"
        )
        self.line_edit.setReadOnly(True)
        self.line_edit.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.line_edit.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.line_edit.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                border: none;
                color: gray;
                padding-left: 4px;
            }
        """)

        self._button_stack = RangeAdjustButtonStack(
            on_increase=lambda: self.sig_increase.emit(),
            on_decrease=lambda: self.sig_decrease.emit(),
            parent=self,
            button_size=QSize(12, 10),
        )

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.line_edit)
        layout.addWidget(self._button_stack)

        if is_clipped or not is_centered:
            self.setToolTip("Requested bounds are clipped by hardware limits")

    def set_selected(self, is_selected: bool):
        color = self.SELECTED_COLOR if is_selected else self.UNSELECTED_COLOR
        self.line_edit.setStyleSheet(
            f"QLineEdit {{ background-color: transparent; border: none; color: {color}; padding-left: 4px; }}"
        )


class VariableTable(QTableWidget):
    sig_sel_changed = pyqtSignal()
    sig_pv_added = pyqtSignal()
    sig_var_config = pyqtSignal(str)
    data_changed = pyqtSignal()
    sig_change_bounds = pyqtSignal(float, str)

    PLACEHOLDER_TEXT = "Enter new variable here...."

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)

        icon_ref = resources.files(__package__) / "../../images/gear.png"
        with resources.as_file(icon_ref) as icon_path:
            self.icon_settings = QIcon(str(icon_path))

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setAutoScroll(False)

        # Reorder the rows by dragging around
        # self.setSelectionBehavior(self.SelectRows)
        # self.setSelectionMode(self.SingleSelection)
        # self.setShowGrid(False)
        # self.setDragDropMode(self.InternalMove)
        # self.setDragDropOverwriteMode(False)

        self.setRowCount(0)
        self.setColumnCount(6)
        self.setAlternatingRowColors(True)
        self.setStyleSheet("alternate-background-color: #262E38;")
        # self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        vheader = self.verticalHeader()
        if vheader:
            vheader.setVisible(False)
        header = self.horizontalHeader()
        if header:
            # header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)

        self.setColumnWidth(0, 20)
        self.setColumnWidth(2, 76)
        self.setColumnWidth(3, 76)
        self.setColumnWidth(4, 76)
        self.setColumnWidth(5, 44)

        # values for horizontal resizing
        self._base_viewport_width: int | None = None
        self._base_col_width = 76
        self._max_col_width = 100
        # cache col widths to avoid duplicate updates
        self._last_col_widths: tuple[int, int, int] = (
            self._base_col_width,
            self._base_col_width,
            self._base_col_width,
        )

        self.setHorizontalHeaderLabels(
            ["", "Name", "Saved", "Current", "Range (Δ)", ""]
        )

        self._init_range_header_controls()

        self.all_variables: list[
            dict[str, tuple[float, float]]
        ] = []  # store all variables
        self.variables: list[
            dict[str, tuple[float, float]]
        ] = []  # store variables to be displayed
        self.selected: dict[str, bool] = {}  # track var selected status
        self.bounds: dict[str, tuple[float, float]] = {}  # track var bounds
        self.clipped: dict[str, bool] = {}
        self.saved_values: dict[str, float] = {}
        self.current_values: dict[str, float] = {}
        self.checked_only = False
        self.bounds_locked = False
        self.addtl_vars = []  # track variables added on the fly
        self.env_class: type[Environment] | None = (
            None  # needed to get bounds on the fly
        )
        self.env = None  # needed to get bounds on the fly
        self.configs = None  # needed to get bounds on the fly
        self.previous_values: dict[
            tuple[int, int], str
        ] = {}  # to track changes in table
        self.config_logic()
        QTimer.singleShot(0, self._capture_resize_baseline)  # get initial table size
        self.customContextMenuRequested.connect(self.display_context_menu)

    def _init_range_header_controls(self) -> None:
        """
        Header buttons for variable range adjustment
        """
        header = self.horizontalHeader()

        self._range_header_widget = QWidget(header.viewport())
        self._range_header_widget.setObjectName("RangeHeaderWidget")
        self._range_header_widget.setStyleSheet("""
            QWidget#RangeHeaderWidget { background-color: transparent; }
            """)
        layout = QHBoxLayout(self._range_header_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self._header_button_stack = RangeAdjustButtonStack(
            on_increase=lambda: self.sig_change_bounds.emit(1.11111, None),
            on_decrease=lambda: self.sig_change_bounds.emit(0.9, None),
            parent=self._range_header_widget,
            button_size=QSize(36, 11),
        )
        header_button_style = """
            QPushButton {
                background-color: #37414F;
                color: #C4CCD4;
                border: 1px solid #54687A;
                border-radius: 1px;
                font-size: 6px;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #54687A;
            }
        """
        self._header_button_stack.up_btn.setStyleSheet(header_button_style)
        self._header_button_stack.down_btn.setStyleSheet(header_button_style)
        self._header_button_stack.up_btn.setToolTip(
            "Scale all selected ranges by * 1.111"
        )
        self._header_button_stack.down_btn.setToolTip(
            "Scale all selected ranges by * 0.9"
        )

        layout.addWidget(
            self._header_button_stack, alignment=Qt.AlignmentFlag.AlignCenter
        )

        header.sectionResized.connect(self._position_range_header_controls)
        header.sectionMoved.connect(self._position_range_header_controls)
        header.geometriesChanged.connect(self._position_range_header_controls)
        self._position_range_header_controls()

    def _position_range_header_controls(self, *_args) -> None:
        """
        Position range header controls in the last column of table header
        """
        header = self.horizontalHeader()

        last_col = self.columnCount() - 1
        if last_col < 0:
            self._range_header_widget.hide()
            return

        section_width = header.sectionSize(last_col)
        x = header.sectionViewportPosition(last_col)
        y = 0
        height = header.height()
        self._range_header_widget.setGeometry(x, y, section_width, height)
        self._range_header_widget.show()

    def update_vocs(self):
        """
        Emit the data_changed signal to notify that the VOCS has been updated.
        """
        logging.debug("Emitting data_changed signal from VariableTable")
        self.data_changed.emit()

    def config_logic(self):
        hheader = self.horizontalHeader()
        if hheader:
            hheader.sectionClicked.connect(self.header_clicked)
        # Catch if any item gets changed
        self.itemChanged.connect(self.add_additional_variable)
        # self.data_changed.connect(self.update_bounds)

    def setItem(self, row: int, column: int, item: QTableWidgetItem | None) -> None:
        if item:
            text = item.text()
            if text != self.PLACEHOLDER_TEXT:
                self.previous_values[(row, column)] = item.text()
        super().setItem(row, column, item)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_column_widths()
        self._position_range_header_controls()

    def _capture_resize_baseline(self) -> None:
        """update startup widths after the initial layout settles."""
        self._base_viewport_width = self.viewport().width()
        self._last_col_widths = (
            self.columnWidth(2),
            self.columnWidth(3),
            self.columnWidth(4),
        )

    def _update_column_widths(self) -> None:
        """
        Smoothly update column 1-4 widths up to maximum, after which only col 1 continues to expand
        """

        # get current width
        current_width = self.viewport().width()
        if self._base_viewport_width is None:
            return

        # calculate extra width needed, return if already at max
        extra_width = max(0, current_width - self._base_viewport_width)
        max_extra = self._max_col_width - self._base_col_width
        if extra_width >= 4 * max_extra and self._last_col_widths == (
            self._max_col_width,
            self._max_col_width,
            self._max_col_width,
        ):
            return

        # distribute extra between cols
        shared_extra = min(extra_width // 4, max_extra)
        remainder = extra_width % 4
        target_width = self._base_col_width + shared_extra
        target_widths = [target_width, target_width, target_width]

        # Distribute leftover pixels for smooth growth during resize
        for i in range(min(remainder, 3)):
            target_widths[i] = min(target_widths[i] + 1, self._max_col_width)

        target_tuple = (target_widths[0], target_widths[1], target_widths[2])
        if target_tuple == self._last_col_widths:
            return

        for col, width in zip((2, 3, 4), target_tuple):
            self.setColumnWidth(col, width)

        self._last_col_widths = target_tuple

    def is_all_checked(self):
        for i in range(self.rowCount() - 1):
            item = self.cellWidget(i, 0)
            if not item:
                raise Exception("Checkbox widget not found!")
            item = cast(QCheckBox, item)
            if not item.isChecked():
                return False

        return True

    def header_clicked(self, idx: int):
        if idx:
            return

        all_checked = self.is_all_checked()

        for i in range(self.rowCount() - 1):
            item = self.cellWidget(i, 0)
            if not item:
                raise Exception("Checkbox widget not found!")
            item = cast(QCheckBox, item)
            # Doing batch update
            item.blockSignals(True)
            item.setChecked(not all_checked)
            item.blockSignals(False)
        self.update_selected()

    def update_bounds(self):
        # Bounds are maintained through self.bounds (not table cells).
        self.data_changed.emit()

    def validate_row(self, row: int):
        """Apply value-cell styling for a row."""
        cb = self.cellWidget(row, 0)
        cb = cast(QCheckBox, cb)
        self._set_cell_value_style(row, cb.isChecked())

    def set_bounds(
        self,
        variables: dict[str, tuple[float, float]],
        signal: bool = True,
        clipped: dict[str, bool] | None = None,
    ):
        clipped = clipped or {}
        for name in variables:
            self.bounds[name] = variables[name]
            if name in clipped:
                self.clipped[name] = clipped[name]
            else:
                self.clipped.pop(name, None)

        if signal:
            self.update_variables(self.variables, 2)
        else:
            self.update_variables(self.variables, 3)

    def refresh_variable(
        self,
        name: str,
        bounds: tuple[float, float],
        hard_bounds: tuple[float, float],
        is_clipped: bool = False,
    ):
        self.bounds[name] = bounds
        self.clipped[name] = is_clipped

        # Update the variable in self.variables
        for var in self.variables:
            if name in var:
                var[name] = hard_bounds
                break

        # Update the variable in self.all_variables
        for var in self.all_variables:
            if name in var:
                var[name] = hard_bounds
                break

        self.update_variables(self.variables, 2)

    def update_selected(self):
        for i in range(self.rowCount() - 1):
            _cb = self.cellWidget(i, 0)
            if not _cb:
                raise Exception("Checkbox widget not found!")
            _cb = cast(QCheckBox, _cb)

            widget = self.item(i, 1)
            if not widget:
                raise Exception("Variable name widget not found!")
            name = widget.text()
            is_selected = _cb.isChecked()
            widget.setForeground(QColor("lightgray" if is_selected else "gray"))
            self._set_cell_value_style(i, is_selected)
            if name != self.PLACEHOLDER_TEXT:  # TODO: fix...
                self.selected[name] = is_selected

        self.sig_sel_changed.emit()
        self.update_vocs()

        if self.checked_only:
            self.show_checked_only()

    def _scroll_to_first_checked_row(self) -> None:
        for row in range(self.rowCount() - 1):
            cb = self.cellWidget(row, 0)
            if not cb:
                continue
            cb = cast(QCheckBox, cb)
            if cb.isChecked():
                item = self.item(row, 1)
                if item is not None:
                    self.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtTop)
                return

    def set_selected(self, variable_names: list[str]):
        self.selected: dict[str, bool] = {}
        for vname in variable_names:
            self.selected[vname] = True

        self.update_variables(self.variables, 3)

    def toggle_show_mode(self, checked_only: bool):
        self.checked_only = checked_only
        if checked_only:
            self.show_checked_only()
        else:
            self.show_all()
            QTimer.singleShot(0, self._scroll_to_first_checked_row)

    def show_checked_only(self):
        checked_variables: list[dict[str, tuple[float, float]]] = []
        for var in self.variables:
            name = next(iter(var))
            if self.is_checked(name):
                checked_variables.append(var)
        self.update_variables(checked_variables, 3)

    def show_all(self):
        self.update_variables(self.variables, 3)

    def is_checked(self, name: str) -> bool:
        try:
            _checked = self.selected[name]
        except KeyError:
            _checked = False

        return _checked

    def get_visible_variables(
        self, variables: list[dict[str, tuple[float, float]]]
    ) -> list[dict[str, tuple[float, float]]]:
        _variables: list[
            dict[str, tuple[float, float]]
        ] = []  # store variables to be displayed
        if self.checked_only:
            for var in variables:
                name = next(iter(var))
                if self.is_checked(name):
                    _variables.append(var)
        else:
            _variables = variables

        return _variables

    def _convert_bounds_to_tuple(self, bounds: Any) -> dict[str, tuple[float, float]]:
        return {k: (v[0], v[1]) for k, v in bounds.items()}

    def set_saved_values(self, values_by_name: dict[str, float]) -> None:
        """Set displayed saved values using a name->value mapping."""
        if not values_by_name:
            return

        for name, value in values_by_name.items():
            if any(name in var for var in self.variables):
                self.saved_values[name] = float(value)

        if self.variables:
            self.update_variables(variables=self.variables, filtered=2)

    def _set_cell_value_style(self, row: int, is_selected: bool):
        """Update Saved/Current/Scan Range style for a row based on selection."""
        name_item = self.item(row, 1)
        if name_item is None:
            return

        alert_level = 0  # self._check_current_vs_saved(name_item.text())
        saved_cell = self.cellWidget(row, 2)
        current_cell = self.cellWidget(row, 3)

        try:
            saved_cell.update_style(is_selected, alert_level)
            current_cell.update_style(is_selected, alert_level)
        except AttributeError as e:
            logger.warning(
                f"cellWidget at row {row} does not have update_style method: {e}"
            )

        scan_range_cell = self.cellWidget(row, 4)
        if isinstance(scan_range_cell, ScanRangeCell):
            scan_range_cell.set_selected(is_selected)

    def _check_current_vs_saved(self, name: str) -> int:
        """
        Returns 1 if the current value and saved value differ by more than
        a rel_diff threshold of 0.001, otherwise returns 0.
        """
        saved = self.saved_values.get(name)
        current = self.current_values.get(name)
        if saved is None or current is None:
            return 0

        denom = max(abs(saved), 1e-12)
        rel_diff = abs(current - saved) / denom
        return 1 if rel_diff > 0.001 else 0  # alert if more than 0.1% change

    def set_scan_range_options(self):
        self.update_variables(self.variables, 2)

    def refresh_current_values(
        self, variable_names: list[str] | None = None, values: list[float] | None = None
    ):
        """
        Refresh current values for variables displayed in the table.

        Parameters
        ----------
        variable_names : list[str] | None
            List of variable names to refresh. If ``None`` or empty,
            updates all variables in ``self.variables``.
        values : list[float] | None
            If values are provided, they are used directly.
            Otherwise if values is None the method queries the environment for current values.

        Returns
        -------
        None
        """
        if self.env_class is None:
            return

        # If no variable names update all
        if not variable_names:
            variable_names = [next(iter(var)) for var in self.variables]

        # get current values
        if values is None:
            # get values from environment
            self.env = instantiate_env(self.env_class, self.configs)
            value_dict = self.env.get_variables(variable_names)
        else:
            # During optimization loop, variable values are passed from the generator
            # so use values if provided rather than querying the environment.
            value_dict = dict(zip(variable_names, values))
        self.current_values.update(value_dict)
        for name, value in value_dict.items():
            if name not in self.saved_values:
                self.saved_values[name] = value

        for row in range(self.rowCount() - 1):
            name_item = self.item(row, 1)
            if name_item is None:
                continue

            name = name_item.text()

            current_cell = self.cellWidget(row, 3)
            if isinstance(current_cell, CurrentValueCell):
                current_cell.set_value(self.current_values.get(name))
                alert_level = 0  # self._check_current_vs_saved(name)
                current_cell.update_style(self.is_checked(name), alert_level)

    def update_variables(
        self,
        variables: list[dict[str, tuple[float, float] | ContinuousVariable]],
        filtered: int = 0,
    ):
        # filtered = 0: completely refresh
        # filtered = 1: filtered by keyword
        # filtered = 2: just rerender based on check status
        # filtered = 3: same as 2 but do not emit the signal

        self.setRowCount(0)

        variables = [self._convert_bounds_to_tuple(var) for var in variables]

        if not filtered:
            self.all_variables = variables or []
            self.variables = self.all_variables[:]  # make a copy
            self.selected = {}
            self.bounds = {}
            self.clipped = {}
            self.saved_values = {}
            self.current_values = {}
            self.addtl_vars: list[str] = []
            for var in self.variables:
                name = next(iter(var))
                self.bounds[name] = var[name]
        elif filtered == 1:
            self.variables = variables or []

        if not variables:
            return

        _variables = self.get_visible_variables(variables)
        if filtered == 0:
            self.refresh_current_values([next(iter(var)) for var in _variables])

        n = len(_variables) + 1
        self.setRowCount(n)
        self.previous_values = {}  # to track changes in table

        for i, var in enumerate(_variables):
            name = next(iter(var))

            self.setCellWidget(i, 0, QCheckBox())

            _cb = self.cellWidget(i, 0)
            if not _cb:
                raise Exception("Checkbox widget not found!")
            _cb = cast(QCheckBox, _cb)

            _cb.setChecked(self.is_checked(name))
            _cb.stateChanged.connect(self.update_selected)
            item = QTableWidgetItem(name)
            if name in self.addtl_vars:
                # Make new PVs a different color
                item.setForeground(QColor("darkCyan"))
            else:
                # Make non-new PVs not editable
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                item.setForeground(QColor("lightgray" if _cb.isChecked() else "gray"))
            self.setItem(i, 1, item)

            if name not in self.saved_values:
                self.saved_values[name] = self.current_values.get(name, 0.0)

            saved_cell = SavedValueCell(self.saved_values.get(name))
            current_cell = CurrentValueCell(self.current_values.get(name))
            scan_range_cell = ScanRangeCell(
                self.current_values.get(name, 0.0),
                self.bounds.get(name, (0.0, 0.0)),
                self.clipped.get(name),
            )
            scan_range_cell.sig_increase.connect(
                lambda var_name=name: self.sig_change_bounds.emit(1.11111, var_name)
            )
            scan_range_cell.sig_decrease.connect(
                lambda var_name=name: self.sig_change_bounds.emit(0.9, var_name)
            )
            self.setCellWidget(i, 2, saved_cell)
            self.setCellWidget(i, 3, current_cell)
            self.setCellWidget(i, 4, scan_range_cell)
            self._set_cell_value_style(i, _cb.isChecked())

            # Add the config button
            config_button = QPushButton()
            config_button.setFixedSize(20, 20)
            config_button.setIcon(self.icon_settings)
            config_button.setIconSize(QSize(12, 12))

            # Center-align the button in the cell
            button_container = QWidget()
            layout = QHBoxLayout(button_container)
            layout.setSpacing(2)
            layout.addWidget(config_button)
            layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
            layout.setContentsMargins(2, 0, 0, 0)  # Remove extra margins
            self.setCellWidget(i, 5, button_container)

            config_button.clicked.connect(partial(self.handle_config_button, name))

        # Make extra editable row
        item = QTableWidgetItem(self.PLACEHOLDER_TEXT)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        item.setForeground(QColor("gray"))
        self.setItem(n - 1, 1, item)

        self.setHorizontalHeaderLabels(
            ["", "Name", "Saved", "Current", "Range (Δ)", ""]
        )
        self.setVerticalHeaderLabels([str(i) for i in range(n)])

        if filtered not in [1, 3]:
            self.sig_sel_changed.emit()
            self.data_changed.emit()

    def handle_config_button(self, var_name: str):
        self.sig_var_config.emit(var_name)

    def add_additional_variable(self, item: QTableWidgetItem):
        row = item.row()
        column = item.column()
        name = item.text()

        if row != self.rowCount() - 1 and column == 1 and name != self.PLACEHOLDER_TEXT:
            # check that the new text is not equal to the previous value at that cell
            prev_name = self.previous_values.get((row, column), "")
            if name == prev_name:
                return
            else:
                # delete row and additional variable
                self.removeRow(row)
                self.addtl_vars.remove(prev_name)
                self.variables = [
                    var for var in self.variables if next(iter(var)) != prev_name
                ]
                del self.bounds[prev_name]
                self.clipped.pop(prev_name, None)
                del self.selected[prev_name]

                self.update_variables(self.variables, 2)
            return

        if row == self.rowCount() - 1 and column == 1 and name != self.PLACEHOLDER_TEXT:
            self.try_insert_variable(name)

    def try_insert_variable(self, name: str):
        idx = self.rowCount() - 1

        # Check that variables doesn't already exist in table
        if name in [next(iter(d)) for d in self.variables]:
            self.update_variables(self.variables, 2)
            QMessageBox.warning(
                self, "Variable already exists!", f"Variable {name} already exists!"
            )
            return

        # Get bounds from interface, if PV exists on interface
        _bounds = None
        _current_value = 0.0
        if self.env_class is not None:
            try:
                value, _bounds = self.get_bounds(name)
                _current_value = float(value)
            except BadgerInterfaceChannelError:
                # Raised when PV does not exist after attempting to call value
                # Revert table to previous state
                self.update_variables(self.variables, 2)
                QMessageBox.critical(
                    self,
                    "Variable Not Found!",
                    f"Variable {name} cannot be found through the interface!",
                )
                return
            except Exception:
                # Raised when PV exists but value/hard limits cannot be found
                # Set to some default values
                _bounds = [0, 0]
                _current_value = 0.0
                detailed_text = (
                    "Encountered issues when tried to fetch bounds for"
                    f" variable {name}. Please manually set the bounds."
                )
                dialog = ExpandableMessageBox(
                    text=detailed_text,
                    detailedText=traceback.format_exc(),
                )
                dialog.setIcon(QMessageBox.Icon.Critical)
                dialog.exec_()

        else:
            # TODO: handle this case? Right now I don't think it should happen
            raise Exception("Environment cannot be found for new variable bounds!")

        # Add checkbox only when a PV is entered
        self.setCellWidget(idx, 0, QCheckBox())

        _cb = self.cellWidget(idx, 0)
        if not _cb:
            raise Exception("Checkbox widget not found!")
        _cb = cast(QCheckBox, _cb)

        # Checked by default when entered
        _cb.setChecked(True)
        self.selected[name] = True

        self.add_variable(name, _bounds[0], _bounds[1])
        self.current_values[name] = _current_value
        self.saved_values.setdefault(name, _current_value)
        self.addtl_vars.append(name)

        self.update_variables(self.variables, 2)

        self.sig_pv_added.emit()  # notify the routine page that a new PV has been added

    def get_bounds(self, name: str) -> tuple[Any, Any]:
        # TODO: move elsewhere?
        self.env = instantiate_env(self.env_class, self.configs)

        value = self.env.get_variable(name)
        bound = self.env.get_bounds([name])[name]
        return value, _round_bounds_inward(bound)

    def add_variable(self, name: str, lb: float, ub: float):
        var = {name: (lb, ub)}

        self.all_variables.append(var)
        self.variables.append(var)
        self.bounds[name] = (lb, ub)

    def export_variables(self) -> dict[str, tuple[float, float]]:
        variables_exported: dict[str, tuple[float, float]] = {}
        for var in self.all_variables:
            name = next(iter(var))
            if self.is_checked(name):
                variables_exported[name] = self.bounds[name]

        return variables_exported

    def lock_bounds(self):
        self.bounds_locked = True
        self.toggle_show_mode(self.checked_only)

    def unlock_bounds(self):
        self.bounds_locked = False
        self.toggle_show_mode(self.checked_only)

    def dragEnterEvent(self, e: QDragEnterEvent | None):
        if e is None:
            return

        mime_data = e.mimeData()
        if not mime_data:
            e.ignore()
            return

        if mime_data.hasText():
            e.acceptProposedAction()
        else:
            e.ignore()

    def dragMoveEvent(self, e: QDragMoveEvent | None):
        if e is None:
            return

        mime_data = e.mimeData()
        if not mime_data:
            e.ignore()
            return

        if mime_data.hasText():
            e.acceptProposedAction()
        else:
            e.ignore()

    def dropEvent(self, event: QDropEvent | None):
        if event is None:
            return

        mime_data = event.mimeData()
        if not mime_data:
            event.ignore()
            return

        if mime_data.hasText():
            text = mime_data.text()
            strings = text.strip().split("\n")

            for string in strings:
                string = string.strip()
                if not string:
                    continue

                variable_names = [item.strip() for item in string.split(",")]
                for name in variable_names:
                    self.try_insert_variable(name)

            event.acceptProposedAction()
        else:
            event.ignore()

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if index.column() == 1:
            flags |= Qt.ItemIsEditable | Qt.ItemIsDropEnabled
        return flags

    def display_info(self, item: QTableWidgetItem | None):
        """
        Opens a message box displaying status info from the underlying interface about a variable.
        """
        if not self.env:
            self.env = instantiate_env(self.env_class, self.configs)

        status = self.env.get_info([item.text()])
        if status is None or len(status["vars"]) < 1:
            return

        mb = QDialog(self)
        mb.setWindowTitle("Variable Info")
        layout = QGridLayout(mb)
        row = 0
        for k, v in status["vars"][item.text()].items():
            layout.addWidget(QLabel(text=f"{k}:", parent=mb), row, 0)
            layout.addWidget(QLabel(text=v, parent=mb), row, 1)
            row += 1

        # Add a close button
        close = QPushButton("Close", mb)
        close.pressed.connect(lambda: self._handle_close(mb))
        layout.addWidget(close, row, 0, 1, 2)

        layout.setRowStretch(row + 1, 1)
        mb.exec()

    @staticmethod
    def _handle_close(widget: QPushButton):
        widget.close()

    def copy_name(self, item: QTableWidgetItem | None):
        if item is None:
            return
        clipboard = QGuiApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(item.text())

    def display_context_menu(self, pt: QPoint):
        menu = QMenu(self)
        item = self.itemAt(pt)
        if item is None or item.text() == self.PLACEHOLDER_TEXT or item.column() != 1:
            return

        info_action = menu.addAction("&Info")
        if info_action is not None:
            info_action.triggered.connect(lambda: self.display_info(item))
        config_action = menu.addAction("&Config")
        if config_action is not None:
            config_action.triggered.connect(
                lambda: self.handle_config_button(item.text())
            )
        menu.addSeparator()
        copy_action = menu.addAction("&Copy")
        if copy_action is not None:
            copy_action.triggered.connect(lambda: self.copy_name(item))
        menu.exec(self.mapToGlobal(pt))
