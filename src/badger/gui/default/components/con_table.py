from typing import Any
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QStyledItemDelegate,
    QDoubleSpinBox,
    QMessageBox,
)

from badger.gui.default.components.editable_table import EditableTable


class ConstraintTable(EditableTable):
    """
    A custom QTableWidget for displaying and managing constraints.

    This table supports:
      - Displaying constraints with relation, threshold, and criticality.
      - Toggling constraints via checkboxes.
      - Batch updating and filtering based on the check status.
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

        self.setColumnCount(5)

        self.setColumnWidth(2, 96)
        self.setColumnWidth(3, 96)
        self.setColumnWidth(4, 64)
        self.setHorizontalHeaderLabels(
            ["", "Name", "Relation", "Threshold", "Critical"]
        )

    def default_info(self) -> list:
        """
        Get the default information list for a new item.

        Returns
        -------
        list
            A list containing default values for a new item.
        """
        return ["<", 0.0, False]

    def new_item_prompt(self):
        """
        The prompt text to enter a new item.
        """
        return "Enter new constraint here..."

    def heads_up(self, name: str) -> None:
        """
        Show a warning message if the item already exists in the table.

        Parameters
        ----------
        name : str
            The name of the item to check.
        """
        QMessageBox.warning(
            self,
            "Constraint already exists!",
            f"Constraint {name} already exists!",
        )

    def create_cell_widgets(self, info: list):
        # Relation
        relation_combo = QComboBox()
        relation_combo.setItemDelegate(QStyledItemDelegate())
        relation_combo.addItems(["<", ">"])
        relation_combo.setCurrentText(info[0])

        # Threshold
        threshold_spinbox = QDoubleSpinBox()
        threshold_spinbox.setDecimals(6)
        threshold_spinbox.setRange(-1e6, 1e6)
        threshold_spinbox.setValue(info[1])

        # Critical
        critical_checkbox = QCheckBox()
        critical_checkbox.setChecked(info[2])

        return [relation_combo, threshold_spinbox, critical_checkbox]
