from typing import Any, List, Dict
from functools import partial
from PyQt5.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QStyledItemDelegate,
    QDoubleSpinBox,
    QMessageBox,
)
from PyQt5.QtCore import Qt, QRegExp
from PyQt5.QtGui import QDropEvent, QDragEnterEvent, QDragMoveEvent, QColor


class EditableTable(QTableWidget):
    """
    A custom QTableWidget that supports editing and managing tabular data.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the EditableTable widget.

        Parameters
        ----------
        *args : Any
            Variable length argument list for QTableWidget.
        **kwargs : Any
            Arbitrary keyword arguments for QTableWidget.
        """
        super().__init__(*args, **kwargs)

        self.setSelectionMode(QAbstractItemView.SingleSelection)

        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragDropOverwriteMode(False)
        self.setAcceptDrops(True)

        self.setRowCount(0)
        self.setColumnCount(2)
        self.setAlternatingRowColors(True)
        self.setStyleSheet("alternate-background-color: #262E38;")

        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.setColumnWidth(0, 20)  # width for checkboxes

        self.data: List[Dict[str, Any]] = []
        self.status: Dict[str, bool] = {}  # track selection
        self.formulas: Dict[str, Dict[str, Any]] = {}  # track formula item

        self.show_selected_only = False
        self.keyword = ""

        self.config_logic()

    def config_logic(self) -> None:
        """
        Configure signal connections and internal logic.
        """
        self.horizontalHeader().sectionClicked.connect(self.header_clicked)
        self.itemChanged.connect(self.on_edit_table_item)

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
        return "Enter new item here..."

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
            "Item already exists!",
            f"Item {name} already exists!",
        )

    def create_cell_widgets(self, info: list):
        # Relation
        relation_combo = QComboBox()
        relation_combo.setItemDelegate(QStyledItemDelegate())
        relation_combo.addItems(["<", ">"])
        relation_combo.setCurrentText(info[0])

        # Threshold
        threshold_spinbox = QDoubleSpinBox()
        threshold_spinbox.setDecimals(4)
        threshold_spinbox.setRange(-1e6, 1e6)
        threshold_spinbox.setValue(info[1])

        # Critical
        critical_checkbox = QCheckBox()
        critical_checkbox.setChecked(info[2])

        return [relation_combo, threshold_spinbox, critical_checkbox]

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """
        Accept the drag event if it contains text or originates from within the table.

        Parameters
        ----------
        event : QDragEnterEvent
            The drag enter event.
        """
        # Accept internal moves (reordering) or external text drops.
        if event.source() == self or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """
        Continue accepting the drag move event if it contains text or is internal.

        Parameters
        ----------
        event : QDragMoveEvent
            The drag move event.
        """
        if event.source() == self or event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        """
        Handle drop events.

        If the drop originates from within the table (i.e. internal move),
        the default row reordering behavior is used. If the drop is external
        and contains text, the text is parsed to create new items.
        Each dropped line is interpreted as an item name, with an optional
        tab-delimited rule (defaulting to "MINIMIZE" if not provided).
        Comma-separated values within each line are treated as separate rows.

        Parameters
        ----------
        event : QDropEvent
            The drop event.
        """
        if event.mimeData().hasText():
            text: str = event.mimeData().text()
            lines = text.splitlines()
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                comma_items = [item.strip() for item in line.split(",")]

                for item in comma_items:
                    if not item:
                        continue

                    parts = item.split("\t")
                    name = parts[0].strip()
                    if not name:
                        continue

                    existing_names = [next(iter(item)) for item in self.data]
                    if name not in existing_names:
                        self.add_plain_item(name)
                    else:
                        self.heads_up(name)

            event.acceptProposedAction()
        else:
            event.ignore()

    @property
    def item_names(self) -> List[str]:
        """
        Get the names of all items in the table.

        Returns
        -------
        List[str]
            A list of item names.
        """
        return [next(iter(item)) for item in self.data]

    def block_signals(func):
        """
        A decorator to block signals at the beginning of a function
        and unblock them at the end.
        """

        def wrapper(self, *args, **kwargs):
            self.blockSignals(True)
            try:
                return func(self, *args, **kwargs)
            finally:
                self.blockSignals(False)

        return wrapper

    def header_clicked(self, idx: int) -> None:
        """
        Toggle the selection of all objectives when the first header is clicked.

        Parameters
        ----------
        idx : int
            The index of the clicked header section. This method only acts if idx is 0.
        """
        if idx != 0:
            return

        all_checked = True
        visible_names = []
        for i in range(self.rowCount() - 1):  # Exclude the last empty row
            checkbox = self.cellWidget(i, 0)
            name_item = self.item(i, 1)
            visible_names.append(name_item.text())
            if not checkbox.isChecked():
                all_checked = False

        for name in visible_names:
            self.status[name] = not all_checked

        self.update_items()

    def insert_item(
        self,
        row: int,
        name: str,
        info: list,
        selected: bool = False,
    ) -> None:
        """
        Insert a new item into the table.

        Parameters
        ----------
        row : int
            The row index where the item should be inserted.
        name : str
            The name of the item.
        info : list
            A list containing additional information about the item.
        selected : bool, optional
            Whether the item is selected, default is False.
        """
        checkbox = QCheckBox()
        checkbox.setChecked(selected)
        self.setCellWidget(row, 0, checkbox)
        checkbox.stateChanged.connect(
            lambda: self.update_selected(name, checkbox.isChecked())
        )

        # Name
        name_item = QTableWidgetItem(name)
        if name in self.formulas:
            # Make new PVs a different color
            name_item.setForeground(QColor("darkCyan"))
        else:
            # Make non-new PVs not editable
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        self.setItem(row, 1, name_item)

        cell_widgets = self.create_cell_widgets(info)
        for i, widget in enumerate(cell_widgets):
            if isinstance(widget, QComboBox):
                widget.currentIndexChanged.connect(partial(self.update_info, i))
            elif isinstance(widget, QDoubleSpinBox):
                widget.valueChanged.connect(partial(self.update_info, i))
            elif isinstance(widget, QCheckBox):
                widget.stateChanged.connect(partial(self.update_info, i))
            else:
                raise NotImplementedError(f"Unsupported widget type: {type(widget)}")
            self.setCellWidget(row, 2 + i, widget)

    @block_signals
    def add_formula_item(self, formula_tuple: tuple) -> None:
        """
        Add a formula-based item to the table.
        Parameters
        ----------
        formula_tuple : tuple
            A tuple containing (name, formula_string, formula_dict)
        """
        try:
            name, formula_string, formula_dict = formula_tuple
            info = self.default_info()
            new_item = {name: info}

            if name in self.item_names:
                self.heads_up(name)
                return

            self.data.append(new_item)
            self.status[name] = True

            self.formulas[name] = {
                "formula": formula_string,
                "variable_mapping": formula_dict,
            }

            # Only insert if the name matches the keyword
            if self.keyword and QRegExp(self.keyword).indexIn(name, 0) == -1:
                return

            # Remove the last row if it exists
            if self.rowCount() > 0:
                self.removeRow(self.rowCount() - 1)

            # Insert the item
            row = self.rowCount()
            self.setRowCount(row + 1)
            self.insert_item(
                row,
                name,
                info=info,
                selected=True,  # Default selection state
            )

            # Add a new empty row for the next item
            self.add_empty_row()

        except (ValueError, TypeError, IndexError) as e:
            print(f"Error adding formula item: {e}")
            return

    def add_plain_item(self, name):
        self.add_formula_item((name, "", {}))

    def get_visible_items(self) -> List[str]:
        """
        Get a list of visible item names based on the current keyword filter.

        Returns
        -------
        List[str]
            A list of visible item names.
        """
        visible_items = []
        rx = QRegExp(self.keyword)

        for item in self.data:
            name = next(iter(item))
            visible = rx.indexIn(name, 0) != -1
            if not visible:
                continue

            selected = self.status.get(name, False)
            if self.show_selected_only and not selected:
                continue

            visible_items.append(name)

        return visible_items

    @block_signals
    def on_edit_table_item(self, item):
        row = item.row()
        column = item.column()
        name = item.text()

        if column != 1:
            item.setText("")
            return

        # If add constraint in the last row
        if row == self.rowCount() - 1 and name:
            # Check if the item already exists
            if name in self.item_names:
                self.heads_up(name)
                self.removeRow(row)
                self.add_empty_row()
                return

            # Add the item to the internal list
            info = self.default_info()
            self.data.append({name: info})
            self.status[name] = True

            self.formulas[name] = {
                "formula": "",
                "variable_mapping": {},
            }

            # Only insert if the name matches the keyword
            if self.keyword and QRegExp(self.keyword).indexIn(name, 0) == -1:
                self.removeRow(row)
                self.add_empty_row()
                return

            self.insert_item(
                row,
                name,
                info=info,
                selected=True,  # Default selection state
            )
            # Add a new editable row for the next item
            self.add_empty_row()
        elif row == self.rowCount() - 1:
            # If the name is empty, recover the last row
            item.setText(self.new_item_prompt())
        elif not name:
            # If name is empty, delete the row and remove from internal lists
            visible_items = self.get_visible_items()
            original_name = visible_items[row]
            self.removeRow(row)
            item_index = next(
                (i for i, item in enumerate(self.data) if original_name in item),
                None,
            )
            if item_index is not None:
                self.data.pop(item_index)
            del self.status[original_name]
            del self.formulas[original_name]
        else:
            # Renaming attempt
            visible_items = self.get_visible_items()
            original_name = visible_items[row]

            if name in self.item_names:
                self.heads_up(name)
                # Recover the original name
                item.setText(original_name)
                return

            # Update the internal items and status dictionaries
            item_index = next(
                (i for i, item in enumerate(self.data) if original_name in item),
                None,
            )
            if item_index is not None:
                self.data[item_index] = {name: self.data[item_index][original_name]}
            self.status[name] = self.status.pop(original_name)
            self.formulas[name] = self.formulas.pop(original_name)
            # Check if the new name is visible under the current filters
            if self.keyword and QRegExp(self.keyword).indexIn(name, 0) == -1:
                self.removeRow(row)

    def add_empty_row(self):
        """
        Add an empty row for entering a new constraint.
        """
        row = self.rowCount()
        self.setRowCount(row + 1)
        item = QTableWidgetItem(self.new_item_prompt())
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        item.setForeground(QColor("gray"))
        self.setItem(row, 1, item)

    def get_item_by_name(self, name: str) -> Dict[str, Any]:
        """
        Retrieve the item dictionary from the items list that matches the given name.

        Parameters
        ----------
        name : str
            The name of the item to retrieve.

        Returns
        -------
        Dict[str, Any]
            The matching item dictionary.

        Raises
        ------
        ValueError
            If no item with the given name is found.
        """
        for item in self.data:
            if name in item:
                return item
        raise ValueError(f"No item found with name: {name}")

    def update_selected(self, name: str, selected: bool) -> None:
        """
        Update the internal status dictionary based on the checkbox states.
        """
        self.status[name] = selected
        if self.show_selected_only:
            self.update_items()

    def update_info(self, idx: int) -> None:
        for i in range(self.rowCount() - 1):
            name_item = self.item(i, 1)
            if name_item is None:
                continue
            name = name_item.text()
            cell_widget = self.cellWidget(i, 2 + idx)
            if cell_widget is not None:
                item = self.get_item_by_name(name)
                if isinstance(cell_widget, QComboBox):
                    value = cell_widget.currentText()
                elif isinstance(cell_widget, QDoubleSpinBox):
                    value = cell_widget.value()
                elif isinstance(cell_widget, QCheckBox):
                    value = cell_widget.isChecked()
                else:
                    raise NotImplementedError(
                        f"Unsupported cell widget type: {type(cell_widget)}"
                    )
                item[name][idx] = value

    def update_show_selected_only(self, show: bool) -> None:
        """
        Update the visibility of constraints based on the selected state.

        Parameters
        ----------
        show : bool
            If True, only show selected constraints; otherwise, show all.
        """
        self.show_selected_only = show
        self.update_items()

    def update_keyword(self, keyword: str) -> None:
        """
        Update the keyword for filtering constraints.

        Parameters
        ----------
        keyword : str
            The keyword to filter constraints by name.
        """
        self.keyword = keyword
        self.update_items()

    @block_signals
    def update_items(self, data=None, status=None, formulas=None) -> None:
        """
        Refresh the table with the current items.
        """
        self.setRowCount(0)

        if data is not None:
            self.data = data
        if status is not None:
            self.status = status
        if formulas is not None:
            self.formulas = formulas

        rx = QRegExp(self.keyword)

        for item in self.data:
            row = self.rowCount()

            name = next(iter(item))
            visible = rx.indexIn(name, 0) != -1
            if not visible:
                continue

            info = item[name]
            selected = self.status.get(name, False)
            if self.show_selected_only and not selected:
                continue

            self.setRowCount(row + 1)
            self.insert_item(
                row,
                name,
                info=info,
                selected=selected,
            )

        # Add an empty row for new constraints
        self.add_empty_row()

    def export_data(self) -> List[Dict[str, Any]]:
        """
        Export the items as a list of dictionaries.

        Returns
        -------
        List[Dict[str, Any]]
            A list of items with their properties.
        """
        exported_items = []
        for item in self.data:
            if self.status.get(next(iter(item)), False):
                exported_items.append(item)
        return exported_items
