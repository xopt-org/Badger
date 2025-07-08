from typing import Any
from PyQt5.QtWidgets import (
    QComboBox,
    QStyledItemDelegate,
    QMessageBox,
)

from badger.gui.default.components.editable_table import EditableTable


class ObjectiveTable(EditableTable):
    """
    A custom QTableWidget for displaying and managing objectives with associated rules.

    This table supports:
      - Displaying objectives along with a rule (e.g., MINIMIZE or MAXIMIZE).
      - Toggling objectives via checkboxes.
      - Batch updating and filtering based on the check status.
      - Internal drag and drop to reorder rows.
      - External drag and drop of text to add new objectives.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the ObjectiveTable widget.

        Parameters
        ----------
        *args : Any
            Variable length argument list for QTableWidget.
        **kwargs : Any
            Arbitrary keyword arguments for QTableWidget.
        """
        super().__init__(*args, **kwargs)

        self.setColumnCount(3)

        self.setColumnWidth(2, 192)
        self.setHorizontalHeaderLabels(["", "Name", "Rule"])

    def default_info(self) -> list:
        """
        Get the default information list for a new item.

        Returns
        -------
        list
            A list containing default values for a new item.
        """
        return ["MINIMIZE"]

    def new_item_prompt(self):
        """
        The prompt text to enter a new item.
        """
        return "Enter new objective here..."

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
            "Objective already exists!",
            f"Objective {name} already exists!",
        )

    def create_cell_widgets(self, info: list):
        # Rule
        cb_rule = QComboBox()
        cb_rule.setItemDelegate(QStyledItemDelegate())
        cb_rule.addItems(["MINIMIZE", "MAXIMIZE"])
        cb_rule.setCurrentIndex(0 if info[0] == "MINIMIZE" else 1)

        return [cb_rule]
