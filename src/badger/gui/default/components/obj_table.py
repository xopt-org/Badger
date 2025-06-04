from typing import Any, List, Dict, Optional
from PyQt5.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QStyledItemDelegate,
)
from PyQt5.QtGui import QDropEvent, QDragEnterEvent, QDragMoveEvent


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

        self.formulas: Dict[str, Dict[str, Any]] = {}

        # Enable row reordering via internal drag and drop.
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setShowGrid(False)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragDropOverwriteMode(False)
        self.setAcceptDrops(True)

        self.setRowCount(0)
        self.setColumnCount(4)
        self.setAlternatingRowColors(True)
        self.setStyleSheet("alternate-background-color: #262E38;")
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.setColumnWidth(0, 20)
        self.setColumnWidth(2, 120)
        self.setColumnWidth(3, 100)

        self.all_objectives: List[Dict[str, str]] = []
        self.objectives: List[Dict[str, str]] = []
        self.selected: Dict[str, bool] = {}  # Track objective selected status.
        self.rules: Dict[str, str] = {}  # Track objective rules.
        self.checked_only: bool = False

        self.config_logic()

    def config_logic(self) -> None:
        """
        Configure signal connections and internal logic.
        """
        self.horizontalHeader().sectionClicked.connect(self.header_clicked)

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

                # Split by comma first to handle comma-separated objectives
                comma_items = [item.strip() for item in line.split(",")]

                for item in comma_items:
                    if not item:
                        continue

                    # Then split by tab to handle rule specification
                    parts = item.split("\t")
                    name = parts[0].strip()
                    if not name:
                        continue

                    # If a rule is provided, use it; otherwise, default to "MINIMIZE".
                    rule = parts[1].strip() if len(parts) > 1 else "MINIMIZE"

                    # Check if objective already exists
                    existing_names = [
                        list(obj.keys())[0] for obj in self.all_objectives
                    ]
                    if name not in existing_names:
                        # Append the new objective.
                        self.all_objectives.append({name: rule})

            self.objectives = self.all_objectives
            self.update_objectives(self.objectives, filtered=0)
            event.acceptProposedAction()
        else:
            event.ignore()

    def add_formula_objective_safe(self, formula_tuple: tuple) -> None:
        """
        Safely add a formula-based objective to the table with error handling.

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

            # Check if objective already exists
            existing_names = [list(obj.keys())[0] for obj in self.all_objectives]
            if name in existing_names:
                # Update existing objective instead of adding duplicate
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

            self.update_objectives(self.objectives, filtered=0)

        except (ValueError, TypeError, IndexError) as e:
            print(f"Error adding formula objective: {e}")
            return

    def update_objectives_safe(
        self,
        objectives: Optional[List[Dict[str, str]]],
        filtered: int = 0,
        formula_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Safely update the table with the given objectives with additional error handling.

        Parameters
        ----------
        objectives : Optional[List[Dict[str, str]]]
            A list of objectives to display. Each objective is a dictionary with a single
            key-value pair mapping the objective name to its rule.
        filtered : int, optional
            The filter mode (0, 1, or 2), by default 0.
        formula_data : Optional[Dict[str, Any]], optional
            Dictionary containing formula details for specific objectives, by default None.
        """
        try:
            self.setRowCount(0)
            self.horizontalHeader().setVisible(False)

            if filtered == 0:
                self.all_objectives = objectives or []
                self.objectives = self.all_objectives
                self.selected = {}
                self.rules = {}
                for obj in self.objectives:
                    name = next(iter(obj))
                    self.rules[name] = obj[name]
            elif filtered == 1:
                self.objectives = objectives or []

            if formula_data and filtered == 0:
                self.formulas.update(formula_data)

            if not objectives:
                return

            current_objectives: List[Dict[str, str]] = []
            if self.checked_only:
                for obj in objectives:
                    name = next(iter(obj))
                    if self.is_checked(name):
                        current_objectives.append(obj)
            else:
                current_objectives = objectives

            n = len(current_objectives)
            self.setRowCount(n)

            for i, obj in enumerate(current_objectives):
                try:
                    name = next(iter(obj))

                    # Create and set checkbox for objective selection.
                    checkbox = QCheckBox()
                    self.setCellWidget(i, 0, checkbox)
                    checkbox.setChecked(self.is_checked(name))
                    checkbox.stateChanged.connect(self.update_selected)

                    # Set the objective name.
                    name_item = QTableWidgetItem(name)
                    self.setItem(i, 1, name_item)

                    # Create and set the rule combo box.
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
                        self.setItem(i, 3, formula_indicator)

                except (StopIteration, RuntimeError, KeyError) as e:
                    print(f"Error processing objective at row {i}: {e}")
                    continue

            self.setHorizontalHeaderLabels(["", "Name", "Rule", "Formula"])
            self.setVerticalHeaderLabels([str(i) for i in range(n)])
            self.horizontalHeader().setVisible(True)

        except Exception as e:
            print(f"Error in update_objectives_safe: {e}")

    def update_selected_safe(self, _: int) -> None:
        """
        Safely update the internal selected dictionary based on checkbox states.

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
                    # Widget or item may have been deleted, skip this row
                    print(f"Error accessing row {i}: {e}")
                    continue

            if self.checked_only:
                self.show_checked_only()

        except Exception as e:
            print(f"Error in update_selected_safe: {e}")

    def update_rules_safe(self) -> None:
        """
        Safely update the internal rules dictionary based on the current selections.
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
                    # Widget or item may have been deleted, skip this row
                    print(f"Error accessing rule at row {i}: {e}")
                    continue

        except Exception as e:
            print(f"Error in update_rules_safe: {e}")

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

    def update_rules(self) -> None:
        """
        Update the internal rules dictionary based on the current selections.

        Iterates through all rows and updates each objective's rule based on the value
        of the combo box in the third column.
        """
        for i in range(self.rowCount()):
            name_item = self.item(i, 1)
            if name_item is None:
                continue
            name = name_item.text()
            rule_widget = self.cellWidget(i, 2)
            if rule_widget is not None:
                self.rules[name] = rule_widget.currentText()

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

    def update_selected(self, _: int) -> None:
        """
        Update the internal selected dictionary based on checkbox states.

        Parameters
        ----------
        _ : int
            A dummy parameter typically representing the checkbox state change.
        """
        for i in range(self.rowCount()):
            checkbox = self.cellWidget(i, 0)
            name_item = self.item(i, 1)
            if checkbox is not None and name_item is not None:
                name = name_item.text()
                self.selected[name] = checkbox.isChecked()

        if self.checked_only:
            self.show_checked_only()

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

    def update_objectives(
        self,
        objectives: Optional[List[Dict[str, str]]],
        filtered: int = 0,
        formula_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Update the table with the given objectives.

        The update behavior depends on the value of the filtered parameter:
          - filtered = 0: Fully refresh the table.
          - filtered = 1: Update based on a keyword filter.
          - filtered = 2: Re-render based on the current check status.

        Parameters
        ----------
        objectives : Optional[List[Dict[str, str]]]
            A list of objectives to display. Each objective is a dictionary with a single
            key-value pair mapping the objective name to its rule.
        filtered : int, optional
            The filter mode (0, 1, or 2), by default 0.
        formula_data : Optional[Dict[str, Any]], optional
            Dictionary containing formula details for specific objectives, by default None.
        """
        self.setRowCount(0)
        self.horizontalHeader().setVisible(False)

        if filtered == 0:
            self.all_objectives = objectives or []
            self.objectives = self.all_objectives
            self.selected = {}
            self.rules = {}
            for obj in self.objectives:
                name = next(iter(obj))
                self.rules[name] = obj[name]
        elif filtered == 1:
            self.objectives = objectives or []

        if formula_data and filtered == 0:
            self.formulas.update(formula_data)

        if not objectives:
            return

        current_objectives: List[Dict[str, str]] = []
        if self.checked_only:
            for obj in objectives:
                name = next(iter(obj))
                if self.is_checked(name):
                    current_objectives.append(obj)
        else:
            current_objectives = objectives

        n = len(current_objectives)
        self.setRowCount(n)
        for i, obj in enumerate(current_objectives):
            name = next(iter(obj))

            # Create and set checkbox for objective selection.
            checkbox = QCheckBox()
            self.setCellWidget(i, 0, checkbox)
            checkbox.setChecked(self.is_checked(name))
            checkbox.stateChanged.connect(self.update_selected)

            # Set the objective name.
            self.setItem(i, 1, QTableWidgetItem(name))

            # Create and set the rule combo box.
            _rule = self.rules.get(name, "MINIMIZE")
            cb_rule = QComboBox()
            cb_rule.setItemDelegate(QStyledItemDelegate())
            cb_rule.addItems(["MINIMIZE", "MAXIMIZE"])
            cb_rule.setCurrentIndex(0 if _rule == "MINIMIZE" else 1)
            cb_rule.currentIndexChanged.connect(self.update_rules)
            self.setCellWidget(i, 2, cb_rule)

            if name in self.formulas:
                formula_indicator = QTableWidgetItem(self.formulas[name]["formula"])
                self.setItem(i, 3, formula_indicator)

        self.setHorizontalHeaderLabels(["", "Name", "Rule", "Formula"])
        self.setVerticalHeaderLabels([str(i) for i in range(n)])
        self.horizontalHeader().setVisible(True)

    def export_objectives(self) -> Dict[str, Any]:
        """
        Extended export to include formula information.

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

    def add_formula_objective(self, formula_tuple: tuple) -> None:
        """
        Add a formula-based objective to the table.

        Parameters
        ----------
        formula_tuple : tuple
            A tuple containing (name, formula_string, formula_dict)
        """
        name, formula_string, formula_dict = formula_tuple

        rule = "MINIMIZE"

        new_objective = {name: rule}

        if self.all_objectives is None:
            self.all_objectives = []
        self.all_objectives.append(new_objective)
        self.objectives = self.all_objectives

        self.formulas[name] = {
            "formula": formula_string,
            "variable_mapping": formula_dict,
        }

        self.update_objectives(self.objectives, filtered=0)

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
