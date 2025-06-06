from typing import Any, List, Dict, Optional
from PyQt5.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QStyledItemDelegate,
    QMessageBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDropEvent, QDragEnterEvent, QDragMoveEvent, QColor


class ObjectiveTable(QTableWidget):
    """
    A custom QTableWidget for displaying and managing objectives with associated rules.

    This table supports:
      - Displaying objectives along with a rule (e.g., MINIMIZE or MAXIMIZE).
      - Toggling objectives via checkboxes.
      - Batch updating and filtering based on the check status.
      - Internal drag and drop to reorder rows.
      - External drag and drop of text to add new objectives.

    Attributes
    ----------
    all_objectives : List[Dict[str, str]]
        The complete list of objectives. Each objective is a dictionary mapping
        the objective name to its rule.
    objectives : List[Dict[str, str]]
        The currently displayed list of objectives.
    selected : Dict[str, bool]
        A dictionary tracking the selected (checked) status of each objective.
    rules : Dict[str, str]
        A dictionary tracking the rule associated with each objective.
    checked_only : bool
        Flag indicating whether only checked objectives should be displayed.
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

        # Enable row reordering via internal drag and drop.
        # self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        # self.setShowGrid(False)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragDropOverwriteMode(False)
        self.setAcceptDrops(True)

        self.setRowCount(0)
        self.setColumnCount(4)
        self.setAlternatingRowColors(True)
        self.setStyleSheet("alternate-background-color: #262E38;")
        # self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.setColumnWidth(0, 20)
        self.setColumnWidth(2, 118)
        self.setColumnWidth(3, 118)
        self.setHorizontalHeaderLabels(["", "Name", "Rule", "Formula"])

        self.all_objectives: List[Dict[str, str]] = []
        self.objectives: List[Dict[str, str]] = []
        self.selected: Dict[str, bool] = {}  # Track objective selected status.
        self.rules: Dict[str, str] = {}  # Track objective rules.
        self.checked_only: bool = False
        self.addtl_objs = []
        self.previous_values = {}  # to track changes in table
        self.formulas: Dict[str, Dict[str, Any]] = {}

        self.config_logic()

    def config_logic(self) -> None:
        """
        Configure signal connections and internal logic.
        """
        self.horizontalHeader().sectionClicked.connect(self.header_clicked)
        # Catch if any item gets changed
        self.itemChanged.connect(self.add_additional_objective)

    def setItem(self, row, column, item):
        text = item.text()
        if text != "Enter new objective here....":
            self.previous_values[(row, column)] = item.text()
        super().setItem(row, column, item)

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
        if event.source() == self:
            # Internal move: allow default behavior for reordering rows.
            super().dropEvent(event)
        elif event.mimeData().hasText():
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

                    # If a rule is provided, use it; otherwise, default to "MINIMIZE".
                    # rule = parts[1].strip() if len(parts) > 1 else "MINIMIZE"

                    existing_names = [
                        list(obj.keys())[0] for obj in self.all_objectives
                    ]
                    if name not in existing_names:
                        # self.all_objectives.append({name: rule})
                        self.add_formula_objective((name, "", {}))

            # self.objectives = self.all_objectives
            # self.update_objectives(self.objectives, filtered=0)
            event.acceptProposedAction()
        else:
            event.ignore()

    def add_formula_objective(self, formula_tuple: tuple) -> None:
        """
        Add a formula-based objective to the table.
        Parameters
        ----------
        formula_tuple : tuple
            A tuple containing (name, formula_string, formula_dict)
        """
        try:
            name, formula_string, formula_dict = formula_tuple

            rule = "MINIMIZE"

            new_objective = {name: rule}

            if self.all_objectives is None:
                self.all_objectives = []

            existing_names = [list(obj.keys())[0] for obj in self.all_objectives]
            if name in existing_names:
                for obj in self.all_objectives:
                    if list(obj.keys())[0] == name:
                        obj[name] = rule
                        break
            else:
                self.all_objectives.append(new_objective)

            self.objectives = self.all_objectives

            self.formulas[name] = {
                "formula": formula_string,
                "variable_mapping": formula_dict,
            }

            self.update_objectives(self.objectives, 2)

        except (ValueError, TypeError, IndexError) as e:
            print(f"Error adding formula objective: {e}")
            return

    def get_visible_objectives(self, objectives):
        _objectives = []  # store objectives to be displayed
        if self.checked_only:
            for obj in objectives:
                name = next(iter(obj))
                if self.is_checked(name):
                    _objectives.append(obj)
        else:
            _objectives = objectives

        return _objectives

    def update_objectives(
        self,
        objectives: Optional[List[Dict[str, str]]],
        filtered: int = 0,
    ) -> None:
        """
        Update the table with the given objectives.
        Parameters
        ----------
        objectives : Optional[List[Dict[str, str]]]
            A list of objectives to display. Each objective is a dictionary with a single
            key-value pair mapping the objective name to its rule.
        filtered : int, optional
            The filter mode (0, 1, or 2), by default 0.
        """
        try:
            self.setRowCount(0)

            if filtered == 0:
                self.all_objectives = objectives or []
                self.objectives = self.all_objectives[:]  # Make a copy
                self.selected = {}
                self.rules = {}
                for obj in self.objectives:
                    name = next(iter(obj))
                    self.rules[name] = obj[name]
            elif filtered == 1:
                self.objectives = objectives or []

            if not objectives:
                return

            _objectives = self.get_visible_objectives(objectives)

            n = len(_objectives) + 1
            self.setRowCount(n)
            self.previous_values = {}  # to track changes in table

            for i, obj in enumerate(_objectives):
                try:
                    name = next(iter(obj))

                    checkbox = QCheckBox()
                    self.setCellWidget(i, 0, checkbox)
                    checkbox.setChecked(self.is_checked(name))
                    checkbox.stateChanged.connect(self.update_selected)

                    name_item = QTableWidgetItem(name)
                    if name in self.addtl_objs:
                        # Make new PVs a different color
                        name_item.setForeground(QColor("darkCyan"))
                    else:
                        # Make non-new PVs not editable
                        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                    self.setItem(i, 1, name_item)

                    _rule = self.rules.get(name, "MINIMIZE")
                    cb_rule = QComboBox()
                    cb_rule.setItemDelegate(QStyledItemDelegate())
                    cb_rule.addItems(["MINIMIZE", "MAXIMIZE"])
                    cb_rule.setCurrentIndex(0 if _rule == "MINIMIZE" else 1)
                    cb_rule.currentIndexChanged.connect(self.update_rules)
                    self.setCellWidget(i, 2, cb_rule)

                    if name in self.formulas:
                        formula_indicator = QTableWidgetItem(
                            self.formulas[name]["formula"]
                        )
                    else:
                        formula_indicator = QTableWidgetItem("")
                    formula_indicator.setFlags(
                        formula_indicator.flags() & ~Qt.ItemIsEditable
                    )
                    self.setItem(i, 3, formula_indicator)

                except (StopIteration, RuntimeError, KeyError) as e:
                    print(f"Error processing objective at row {i}: {e}")
                    continue

            # Make extra editable row
            item = QTableWidgetItem("Enter new objective here....")
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            item.setForeground(QColor("gray"))
            self.setItem(n - 1, 1, item)

            self.setVerticalHeaderLabels([str(i) for i in range(n)])

        except Exception as e:
            print(f"Error in update_objectives: {e}")

    def update_selected(self, _: int) -> None:
        """
        Update the internal selected dictionary based on checkbox states.
        Parameters
        ----------
        _ : int
            A dummy parameter typically representing the checkbox state change.
        """
        try:
            for i in range(self.rowCount()):
                try:
                    checkbox = self.cellWidget(i, 0)
                    name_item = self.item(i, 1)

                    if checkbox is not None and name_item is not None:
                        name = name_item.text()
                        self.selected[name] = checkbox.isChecked()
                except (RuntimeError, AttributeError) as e:
                    print(f"Error accessing row {i}: {e}")
                    continue

            if self.checked_only:
                self.show_checked_only()

        except Exception as e:
            print(f"Error in update_selected: {e}")

    def update_rules(self) -> None:
        """
        Update the internal rules dictionary based on the current selections.
        """
        try:
            for i in range(self.rowCount()):
                try:
                    name_item = self.item(i, 1)
                    if name_item is None:
                        continue

                    name = name_item.text()
                    rule_widget = self.cellWidget(i, 2)

                    if rule_widget is not None:
                        self.rules[name] = rule_widget.currentText()
                except (RuntimeError, AttributeError) as e:
                    print(f"Error accessing rule at row {i}: {e}")
                    continue

        except Exception as e:
            print(f"Error in update_rules: {e}")

    def is_all_checked(self) -> bool:
        """
        Check if all objectives are selected.

        Returns
        -------
        bool
            True if every objective's checkbox is checked, False otherwise.
        """
        for i in range(self.rowCount()):
            widget = self.cellWidget(i, 0)
            if widget is not None and not widget.isChecked():
                return False
        return True

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

        all_checked = self.is_all_checked()

        for i in range(self.rowCount()):
            widget = self.cellWidget(i, 0)
            if widget is not None:
                widget.blockSignals(True)
                widget.setChecked(not all_checked)
                widget.blockSignals(False)
        self.update_selected(0)

    def set_rules(self, objectives: Dict[str, str]) -> None:
        """
        Set the rules for objectives.

        Parameters
        ----------
        objectives : Dict[str, str]
            A dictionary mapping objective names to their corresponding rules.
        """
        for name in objectives:
            self.rules[name] = objectives[name]
        self.update_objectives(self.objectives, filtered=2)

    def set_selected(self, objective_names: List[str]) -> None:
        """
        Set the selected status for given objectives.

        Parameters
        ----------
        objective_names : List[str]
            A list of objective names to mark as selected.
        """
        self.selected = {}
        for name in objective_names:
            self.selected[name] = True

        self.update_objectives(self.objectives, filtered=2)

    def toggle_show_mode(self, checked_only: bool) -> None:
        """
        Toggle the display mode between showing all objectives and only checked ones.

        Parameters
        ----------
        checked_only : bool
            If True, display only checked objectives; otherwise, display all.
        """
        self.checked_only = checked_only
        if checked_only:
            self.show_checked_only()
        else:
            self.show_all()

    def show_checked_only(self) -> None:
        """
        Filter and display only the objectives that are checked.
        """
        checked_objectives: List[Dict[str, str]] = []
        for obj in self.objectives:
            name = next(iter(obj))
            if self.is_checked(name):
                checked_objectives.append(obj)
        self.update_objectives(checked_objectives, filtered=2)

    def show_all(self) -> None:
        """
        Display all objectives.
        """
        self.update_objectives(self.objectives, filtered=2)

    def is_checked(self, name: str) -> bool:
        """
        Check if the given objective is selected.

        Parameters
        ----------
        name : str
            The name of the objective.

        Returns
        -------
        bool
            True if the objective is checked, False otherwise.
        """
        try:
            return self.selected[name]
        except KeyError:
            return False

    def add_additional_objective(self, item):
        row = idx = item.row()
        column = item.column()
        name = item.text()

        if (
            row != self.rowCount() - 1
            and column == 1
            and name != "Enter new objective here...."
        ):
            # check that the new text is not equal to the previous value at that cell
            prev_name = self.previous_values.get((row, column), "")
            if name == prev_name:
                return
            else:
                # delete row and additional objective
                self.removeRow(row)
                self.addtl_objs.remove(prev_name)
                self.objectives = [
                    var for var in self.objectives if next(iter(var)) != prev_name
                ]
                del self.rules[prev_name]
                del self.selected[prev_name]

                self.update_objectives(self.objectives, 2)
            return

        if (
            row == self.rowCount() - 1
            and column == 1
            and name != "Enter new objective here...."
        ):
            # Check that objectives doesn't already exist in table
            if name in [list(d.keys())[0] for d in self.objectives]:
                self.update_objectives(self.objectives, 2)
                QMessageBox.warning(
                    self,
                    "Objective already exists!",
                    f"Objective {name} already exists!",
                )
                return

            # TODO: Check if the entered name exists in the interface

            # Add checkbox only when a PV is entered
            self.setCellWidget(idx, 0, QCheckBox())

            _cb = self.cellWidget(idx, 0)

            # Checked by default when entered
            _cb.setChecked(True)
            self.selected[name] = True

            _cb.stateChanged.connect(self.update_selected)

            # Create and set the rule combo box.
            _rule = self.rules.get(name, "MINIMIZE")
            cb_rule = QComboBox()
            cb_rule.setItemDelegate(QStyledItemDelegate())
            cb_rule.addItems(["MINIMIZE", "MAXIMIZE"])
            cb_rule.setCurrentIndex(0 if _rule == "MINIMIZE" else 1)
            cb_rule.currentIndexChanged.connect(self.update_rules)
            self.setCellWidget(idx, 2, cb_rule)

            if name in self.formulas:
                formula_indicator = QTableWidgetItem(self.formulas[name]["formula"])
            else:
                formula_indicator = QTableWidgetItem("")
            formula_indicator.setFlags(formula_indicator.flags() & ~Qt.ItemIsEditable)
            self.setItem(idx, 3, formula_indicator)

            self.add_objective(name, _rule)
            self.addtl_objs.append(name)

            self.update_objectives(self.objectives, 2)

    def add_objective(self, name, rule="MINIMIZE") -> None:
        obj = {name: rule}

        self.all_objectives.append(obj)
        self.objectives.append(obj)
        self.rules[name] = rule

    def export_objectives(self) -> Dict[str, Any]:
        """
        Export the selected objectives along with their rules.

        Returns
        -------
        Dict[str, Any]
            Dictionary with selected objectives, their rules, and formula details if applicable.
        """
        exported = {"objectives": {}, "formulas": {}}

        for obj in self.all_objectives:
            name = next(iter(obj))
            if self.is_checked(name):
                exported["objectives"][name] = self.rules.get(name, "MINIMIZE")

                if name in self.formulas:
                    exported["formulas"][name] = self.formulas[name]

        return exported

    def get_formula(self, objective_name: str) -> Optional[Dict[str, Any]]:
        """
        Get formula details for a specific objective.

        Parameters
        ----------
        objective_name : str
            The name of the objective.

        Returns
        -------
        Optional[Dict[str, Any]]
            Formula details if the objective has an associated formula, None otherwise.
        """
        return self.formulas.get(objective_name)

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if index.column() == 1:
            flags |= Qt.ItemIsEditable | Qt.ItemIsDropEnabled
        return flags
