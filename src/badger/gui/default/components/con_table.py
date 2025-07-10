from typing import Any, List, Dict
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


class ConstraintTable(QTableWidget):
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

        self.setSelectionMode(QAbstractItemView.SingleSelection)

        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragDropOverwriteMode(False)
        self.setAcceptDrops(True)

        self.setRowCount(0)
        self.setColumnCount(5)
        self.setAlternatingRowColors(True)
        self.setStyleSheet("alternate-background-color: #262E38;")

        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.setColumnWidth(0, 20)
        self.setColumnWidth(2, 96)
        self.setColumnWidth(3, 96)
        self.setColumnWidth(4, 64)
        self.setHorizontalHeaderLabels(
            ["", "Name", "Relation", "Threshold", "Critical"]
        )

        self.constraints: List[Dict[str, Any]] = []
        self.status: Dict[str, bool] = {}  # Track selection
        self.formulas: Dict[str, Dict[str, Any]] = {}  # Track formula constraints

        self.show_selected_only = False
        self.keyword = ""

        self.config_logic()

    def config_logic(self) -> None:
        """
        Configure signal connections and internal logic.
        """
        self.horizontalHeader().sectionClicked.connect(self.header_clicked)
        self.itemChanged.connect(self.on_edit_table_item)

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
        and contains text, the text is parsed to create new objectives.
        Each dropped line is interpreted as an objective name, with an optional
        tab-delimited rule (defaulting to "MINIMIZE" if not provided).
        Comma-separated values within each line are treated as separate objectives.

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

                    existing_names = [next(iter(con)) for con in self.constraints]
                    if name not in existing_names:
                        self.add_plain_constraint(name)
                    else:
                        QMessageBox.warning(
                            self,
                            "Constraint already exists!",
                            f"Constraint {name} already exists!",
                        )

            event.acceptProposedAction()
        else:
            event.ignore()

    @property
    def constraint_names(self) -> List[str]:
        """
        Get the names of all constraints in the table.

        Returns
        -------
        List[str]
            A list of constraint names.
        """
        return [next(iter(constraint)) for constraint in self.constraints]

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

        self.update_constraints()

    def insert_constraint_item(
        self,
        row: int,
        name: str,
        relation: str = "<",
        threshold: float = 0.0,
        critical: bool = False,
        selected: bool = False,
    ) -> None:
        """
        Insert a new constraint into the table.

        Parameters
        ----------
        row : int
            The row index where the constraint should be inserted.
        name : str
            The name of the constraint.
        relation : str, optional
            The relation for the constraint, default is "<".
        threshold : float, optional
            The threshold value for the constraint, default is 0.0.
        critical : bool, optional
            Whether the constraint is critical, default is False.
        selected : bool, optional
            Whether the constraint is selected, default is False.
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

        # Relation
        relation_combo = QComboBox()
        relation_combo.setItemDelegate(QStyledItemDelegate())
        relation_combo.addItems(["<", ">"])
        relation_combo.setCurrentText(relation)
        relation_combo.currentIndexChanged.connect(self.update_relations)
        self.setCellWidget(row, 2, relation_combo)

        # Threshold
        threshold_spinbox = QDoubleSpinBox()
        threshold_spinbox.setDecimals(6)
        threshold_spinbox.setRange(-1e6, 1e6)
        threshold_spinbox.setValue(threshold)
        threshold_spinbox.valueChanged.connect(self.update_thresholds)
        self.setCellWidget(row, 3, threshold_spinbox)

        # Critical
        critical_checkbox = QCheckBox()
        critical_checkbox.setChecked(critical)
        critical_checkbox.stateChanged.connect(self.update_critical)
        self.setCellWidget(row, 4, critical_checkbox)

    @block_signals
    def add_formula_constraint(self, formula_tuple: tuple) -> None:
        """
        Add a formula-based constraint to the table.
        Parameters
        ----------
        formula_tuple : tuple
            A tuple containing (name, formula_string, formula_dict)
        """
        try:
            name, formula_string, formula_dict = formula_tuple
            new_constraint = {name: ["<", 0.0, False]}

            if name in self.constraint_names:
                QMessageBox.warning(
                    self,
                    "Constraint already exists!",
                    f"Constraint {name} already exists!",
                )
                return

            self.constraints.append(new_constraint)
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

            # Insert the constraint item
            row = self.rowCount()
            self.setRowCount(row + 1)
            self.insert_constraint_item(
                row,
                name,
                relation="<",  # Default relation
                threshold=0.0,  # Default threshold
                critical=False,  # Default criticality
                selected=True,  # Default selection state
            )

            # Add a new empty row for the next constraint
            self.add_empty_row()

        except (ValueError, TypeError, IndexError) as e:
            print(f"Error adding formula constraint: {e}")
            return

    def add_plain_constraint(self, name):
        self.add_formula_constraint((name, "", {}))

    def get_visible_constraints(self) -> List[str]:
        """
        Get a list of visible constraint names based on the current keyword filter.

        Returns
        -------
        List[str]
            A list of visible constraint names.
        """
        visible_constraints = []
        rx = QRegExp(self.keyword)

        for constraint in self.constraints:
            name = next(iter(constraint))
            visible = rx.indexIn(name, 0) != -1
            if not visible:
                continue

            selected = self.status.get(name, False)
            if self.show_selected_only and not selected:
                continue

            visible_constraints.append(name)

        return visible_constraints

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
            # Check if the constraint already exists
            if name in self.constraint_names:
                QMessageBox.warning(
                    self,
                    "Constraint already exists!",
                    f"Constraint {name} already exists!",
                )
                self.removeRow(row)
                self.add_empty_row()
                return

            # Add the constraint to the internal list
            self.constraints.append({name: ["<", 0.0, False]})
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

            self.insert_constraint_item(
                row,
                name,
                relation="<",  # Default relation
                threshold=0.0,  # Default threshold
                critical=False,  # Default criticality
                selected=True,  # Default selection state
            )
            # Add a new editable row for the next constraint
            self.add_empty_row()
        elif row == self.rowCount() - 1:
            # If the name is empty, recover the last row
            item.setText("Enter new constraint here...")
        elif not name:
            # If name is empty, delete the row and remove from internal lists
            visible_constraints = self.get_visible_constraints()
            original_name = visible_constraints[row]
            self.removeRow(row)
            constraint_index = next(
                (i for i, con in enumerate(self.constraints) if original_name in con),
                None,
            )
            if constraint_index is not None:
                self.constraints.pop(constraint_index)
            del self.status[original_name]
            del self.formulas[original_name]
        else:
            # Renaming attempt
            visible_constraints = self.get_visible_constraints()
            original_name = visible_constraints[row]

            if name in self.constraint_names:
                QMessageBox.warning(
                    self,
                    "Constraint already exists!",
                    f"Constraint {name} already exists!",
                )
                # Recover the original name
                item.setText(original_name)
                return

            # Update the internal constraints and status dictionaries
            constraint_index = next(
                (i for i, con in enumerate(self.constraints) if original_name in con),
                None,
            )
            if constraint_index is not None:
                self.constraints[constraint_index] = {
                    name: self.constraints[constraint_index][original_name]
                }
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
        item = QTableWidgetItem("Enter new constraint here...")
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        item.setForeground(QColor("gray"))
        self.setItem(row, 1, item)

    def get_constraint_by_name(self, name: str) -> Dict[str, Any]:
        """
        Retrieve the constraint dictionary from the constraints list that matches the given name.

        Parameters
        ----------
        name : str
            The name of the constraint to retrieve.

        Returns
        -------
        Dict[str, Any]
            The matching constraint dictionary.

        Raises
        ------
        ValueError
            If no constraint with the given name is found.
        """
        for constraint in self.constraints:
            if name in constraint:
                return constraint
        raise ValueError(f"No constraint found with name: {name}")

    def update_selected(self, name: str, selected: bool) -> None:
        """
        Update the internal status dictionary based on the checkbox states.
        """
        self.status[name] = selected
        if self.show_selected_only:
            self.update_constraints()

    def update_relations(self):
        """
        Update the internal relations dictionary based on the combo box selections.
        """
        for i in range(self.rowCount() - 1):
            name_item = self.item(i, 1)
            if name_item is None:
                continue
            name = name_item.text()
            relation_widget = self.cellWidget(i, 2)
            if relation_widget is not None:
                constraint = self.get_constraint_by_name(name)
                constraint[name][0] = relation_widget.currentText()

    def update_thresholds(self):
        """
        Update the internal thresholds dictionary based on the spin box values.
        """
        for i in range(self.rowCount() - 1):
            name_item = self.item(i, 1)
            if name_item is None:
                continue
            name = name_item.text()
            threshold_widget = self.cellWidget(i, 3)
            if threshold_widget is not None:
                constraint = self.get_constraint_by_name(name)
                constraint[name][1] = threshold_widget.value()

    def update_critical(self):
        """
        Update the internal critical dictionary based on the checkbox states.
        """
        for i in range(self.rowCount() - 1):
            name_item = self.item(i, 1)
            if name_item is None:
                continue
            name = name_item.text()
            critical_widget = self.cellWidget(i, 4)
            if critical_widget is not None:
                constraint = self.get_constraint_by_name(name)
                constraint[name][2] = critical_widget.isChecked()

    def update_show_selected_only(self, show: bool) -> None:
        """
        Update the visibility of constraints based on the selected state.

        Parameters
        ----------
        show : bool
            If True, only show selected constraints; otherwise, show all.
        """
        self.show_selected_only = show
        self.update_constraints()

    def update_keyword(self, keyword: str) -> None:
        """
        Update the keyword for filtering constraints.

        Parameters
        ----------
        keyword : str
            The keyword to filter constraints by name.
        """
        self.keyword = keyword
        self.update_constraints()

    @block_signals
    def update_constraints(self, constraints=None, status=None, formulas=None) -> None:
        """
        Refresh the table with the current constraints.
        """
        self.setRowCount(0)

        if constraints is not None:
            self.constraints = constraints
        if status is not None:
            self.status = status
        if formulas is not None:
            self.formulas = formulas

        rx = QRegExp(self.keyword)

        for constraint in self.constraints:
            row = self.rowCount()

            name = next(iter(constraint))
            visible = rx.indexIn(name, 0) != -1
            if not visible:
                continue

            relation, threshold, critical = constraint[name]
            selected = self.status.get(name, False)
            if self.show_selected_only and not selected:
                continue

            self.setRowCount(row + 1)
            self.insert_constraint_item(
                row,
                name,
                relation=relation,
                threshold=threshold,
                critical=critical,
                selected=selected,
            )

        # Add an empty row for new constraints
        self.add_empty_row()

    def export_constraints(self) -> List[Dict[str, Any]]:
        """
        Export the constraints as a list of dictionaries.

        Returns
        -------
        List[Dict[str, Any]]
            A list of constraints with their properties.
        """
        exported_constraints = []
        for constraint in self.constraints:
            if self.status.get(next(iter(constraint)), False):
                exported_constraints.append(constraint)
        return exported_constraints
