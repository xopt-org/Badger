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
from PyQt5.QtCore import Qt
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
        self.status: Dict[str, List[bool]] = {}  # Track visibility and selection
        self.formulas: Dict[str, Dict[str, Any]] = {}  # Track formula constraints

        self.config_logic()

    def config_logic(self) -> None:
        """
        Configure signal connections and internal logic.
        """
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
        # checkbox.stateChanged.connect(self.update_selected)

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
        threshold_spinbox.setDecimals(4)
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
            self.status[name] = [True, True]  # [visible, selected]

            self.formulas[name] = {
                "formula": formula_string,
                "variable_mapping": formula_dict,
            }

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

    @block_signals
    def on_edit_table_item(self, item):
        row = item.row()
        column = item.column()
        name = item.text()

        # If add constraint in the last row
        if row == self.rowCount() - 1 and column == 1 and name:
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
            self.status[name] = [True, True]

            self.formulas[name] = {
                "formula": "",
                "variable_mapping": {},
            }

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

    def update_relations(self):
        """
        Update the internal relations dictionary based on the combo box selections.
        """
        for i in range(self.rowCount() - 1):
            name_item = self.item(i, 0)
            if name_item is None:
                continue
            name = name_item.text()
            relation_widget = self.cellWidget(i, 1)
            if relation_widget is not None:
                self.relations[name] = relation_widget.currentText()

    def update_thresholds(self):
        """
        Update the internal thresholds dictionary based on the spin box values.
        """
        for i in range(self.rowCount() - 1):
            name_item = self.item(i, 0)
            if name_item is None:
                continue
            name = name_item.text()
            threshold_widget = self.cellWidget(i, 2)
            if threshold_widget is not None:
                self.thresholds[name] = threshold_widget.value()

    def update_critical(self):
        """
        Update the internal critical dictionary based on the checkbox states.
        """
        for i in range(self.rowCount() - 1):
            name_item = self.item(i, 0)
            if name_item is None:
                continue
            name = name_item.text()
            critical_widget = self.cellWidget(i, 3)
            if critical_widget is not None:
                self.critical[name] = critical_widget.isChecked()

    @block_signals
    def update_constraints(
        self, constraints=None, status=None, show_selected_only=False
    ) -> None:
        """
        Refresh the table with the current constraints.
        """
        self.setRowCount(0)

        if constraints is not None:
            self.constraints = constraints
        if status is not None:
            self.status = status

        for constraint in self.constraints:
            row = self.rowCount()

            name = next(iter(constraint))
            relation, threshold, critical = constraint[name]
            try:
                visible, selected = self.status[name]
            except KeyError:
                visible, selected = True, False

            if not visible:
                continue

            if show_selected_only and not selected:
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
            if self.selected.get(constraint["name"], False):
                exported_constraints.append(constraint)
        return exported_constraints
