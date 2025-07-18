from typing import Any
from PyQt5.QtWidgets import (
    QMessageBox,
)

from badger.gui.default.components.editable_table import EditableTable


class ObservableTable(EditableTable):
    """
    A custom QTableWidget for displaying and managing observables with associated rules.

    This table supports:
      - Displaying observables.
      - Toggling observables via checkboxes.
      - Batch updating and filtering based on the check status.
      - Internal drag and drop to reorder rows.
      - External drag and drop of text to add new observables.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the ObservableTable widget.

        Parameters
        ----------
        *args : Any
            Variable length argument list for QTableWidget.
        **kwargs : Any
            Arbitrary keyword arguments for QTableWidget.
        """
        super().__init__(*args, **kwargs)

        self.setColumnCount(2)

        self.setHorizontalHeaderLabels(["", "Name"])

    def default_info(self) -> list:
        """
        Get the default information list for a new item.

        Returns
        -------
        list
            A list containing default values for a new item.
        """
        return []

    def new_item_prompt(self):
        """
        The prompt text to enter a new item.
        """
        return "Enter new observable here..."

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
            "Observable already exists!",
            f"Observable {name} already exists!",
        )

    def create_cell_widgets(self, info: list):
        return []
