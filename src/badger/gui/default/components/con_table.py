from importlib import resources
from typing import Any, List, Tuple
from PyQt5.QtCore import (
    pyqtSlot,
    Qt,
)
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QAbstractSpinBox,
    QDoubleSpinBox,
    QTableWidget,
    QAbstractItemView,
    QCheckBox,
    QPushButton,
    QStyledItemDelegate,
    QWidget,
    QHBoxLayout,
)

from badger.gui.default.utils import (
    MouseWheelWidgetAdjustmentGuard,
    NoHoverFocusComboBox,
)


CONS_RELATION_DICT = {
    ">": "GREATER_THAN",
    "<": "LESS_THAN",
    "=": "EQUAL_TO",
}

REMOVE_BUTTON_WIDTH = 32


class ConstraintTable(QTableWidget):
    """
    A custom QTableWidget for displaying and managing constraints.

    This table supports:
      - Displaying constraint names, relations, and thresholds.
      - Toggling constraint criticality via checkboxes.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the ConstraintTable widget.

        Parameters
        ----------
        *args : Any
            Variable length argument list for QTableWidget.
        **kwargs : Any
            Arbitrary keyword arguments for QTableWidget.
        """
        super().__init__(*args, **kwargs)

        icon_ref = resources.files(__package__) / "../images/trash.png"
        with resources.as_file(icon_ref) as icon_path:
            self.icon_trash = QIcon(str(icon_path))

        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setShowGrid(False)

        self.setRowCount(0)
        self.setColumnCount(5)
        self.setAlternatingRowColors(True)
        self.setStyleSheet("alternate-background-color: #262E38;")
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.setColumnWidth(0, 20)
        self.setColumnWidth(1, 192)
        self.setColumnWidth(2, 64)
        self.setColumnWidth(4, 32)

        self.verticalHeader().setVisible(False)
        self.update_header_visibility()

    def update_header_visibility(self):
        self.setHorizontalHeaderLabels(["Crit.", "Name", "Relation", "Threshold", ""])
        self.horizontalHeader().setVisible(self.rowCount() > 0)

    def add_constraint(
        self, options, name=None, relation=0, threshold=0, critical=False, decimals=4
    ) -> None:
        """
        Adds a constraint.
        """
        currentRow = self.rowCount()
        self.setRowCount(self.rowCount() + 1)

        check_crit = QCheckBox()
        check_crit.setChecked(critical)
        self.setCellWidget(currentRow, 0, check_crit)

        cb_obs = NoHoverFocusComboBox()
        cb_obs.setItemDelegate(QStyledItemDelegate())
        cb_obs.addItems(options)
        try:
            idx = options.index(name)
        except:
            idx = 0
        cb_obs.setCurrentIndex(idx)
        self.setCellWidget(currentRow, 1, cb_obs)

        cb_rel = NoHoverFocusComboBox()
        cb_rel.setItemDelegate(QStyledItemDelegate())
        cb_rel.addItems(CONS_RELATION_DICT.keys())
        cb_rel.setFixedWidth(64)
        cb_rel.setCurrentIndex(relation)
        self.setCellWidget(currentRow, 2, cb_rel)

        sb = QDoubleSpinBox()
        sb.setDecimals(decimals)
        sb.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        sb.installEventFilter(MouseWheelWidgetAdjustmentGuard(sb))
        default_value = threshold
        lb = default_value - 1e3
        ub = default_value + 1e3
        sb.setRange(lb, ub)
        sb.setStepType(QAbstractSpinBox.AdaptiveDecimalStepType)
        sb.setValue(default_value)
        self.setCellWidget(currentRow, 3, sb)

        btn_del = QPushButton(self.icon_trash, None)
        btn_del.setFixedSize(REMOVE_BUTTON_WIDTH, 24)
        btn_del.clicked.connect(self.remove_constraint_clicked)
        btn_del_container = QWidget()
        btn_del_layout = QHBoxLayout(btn_del_container)
        btn_del_layout.addWidget(btn_del)
        btn_del_layout.setAlignment(Qt.AlignLeft)
        btn_del_layout.setContentsMargins(2, 0, 0, 0)
        self.setCellWidget(self.rowCount() - 1, 4, btn_del_container)

        self.update_header_visibility()
        self.hide_all_remove_buttons()

    @pyqtSlot()
    def remove_constraint_clicked(self):
        self.update_header_visibility()
        button = self.sender()
        if button:
            row = self.indexAt(button.pos()).row()
            self.removeRow(row)
            self.hide_all_remove_buttons()
            if (button := self.cellWidget(row, 4)) is not None:
                button.setFixedWidth(REMOVE_BUTTON_WIDTH)

    def hide_all_remove_buttons(self):
        for i in range(self.rowCount()):
            self.cellWidget(i, 4).setFixedWidth(0)

    def mouseMoveEvent(self, e):
        self.hide_all_remove_buttons()
        row = self.indexAt(e.localPos().toPoint()).row()
        if (button := self.cellWidget(row, 4)) is not None:
            button.setFixedWidth(REMOVE_BUTTON_WIDTH)
        return super().mouseMoveEvent(e)

    def export_constraints(self) -> List[Tuple[str, int, float, bool, float]]:
        """
        Export the selected constraints.

        Returns
        -------
        List[Tuple[str, int, float, bool, float]]
            The list of constraints.
        """
        constraints_exported: List[Tuple[str, int, float, bool, float]] = []
        for i in range(self.rowCount()):
            constraints_exported.append(
                (
                    self.cellWidget(i, 1).currentText(),
                    CONS_RELATION_DICT[self.cellWidget(i, 2).currentText()],
                    self.cellWidget(i, 3).value(),
                    self.cellWidget(i, 0).isChecked(),
                    self.cellWidget(i, 3).decimals(),
                )
            )
        return constraints_exported

    def clear_constraints(self):
        self.setRowCount(0)
        self.update_header_visibility()
