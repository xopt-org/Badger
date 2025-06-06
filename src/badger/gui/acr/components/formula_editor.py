import re
from typing import Dict, List, Optional
from qtpy.QtGui import QKeyEvent
from qtpy.QtCore import Qt, Slot, QObject, QAbstractTableModel, QModelIndex, Signal
from qtpy.QtWidgets import (
    QDialog,
    QLineEdit,
    QTableView,
    QGridLayout,
    QHeaderView,
    QPushButton,
    QVBoxLayout,
    QHBoxLayout,
    QAbstractItemView,
    QLabel,
)

stylesheet_add = """
QPushButton:hover:pressed
{
    background-color: #4DB6AC;
}
QPushButton:hover
{
    background-color: #26A69A;
}
QPushButton
{
    color: #FFFFFF;
    background-color: #00897B;
}
"""

stylesheet_clear = """
QPushButton:hover:pressed
{
    background-color: #C7737B;
}
QPushButton:hover
{
    background-color: #BF616A;
}
QPushButton
{
    background-color: #A9444E;
}
"""


class VariableModel(QAbstractTableModel):
    """Model to display variables from a table for use in formulas"""

    def __init__(self, variable_names: List[str] = None) -> None:
        """
        Initialize the model with variable names

        Parameters:
        -----------
        variable_names : List[str]
            a list of variable names
        """
        super().__init__()
        self._headers: List[str] = ["Formula Variable", "Observable Name"]
        self._variable_names: List[str] = variable_names or []
        self._formula_names: List[str] = [
            f"{{{i}}}" for i in range(len(self._variable_names))
        ]

    def set_variable_names(self, variable_names: List[str]) -> None:
        """Set the variable names directly

        Parameters:
        -----------
        variable_names : List[str]
            List of variable names
        """
        self.beginResetModel()
        self._variable_names = variable_names
        self._formula_names = [f"{{{i}}}" for i in range(len(self._variable_names))]
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of variables"""
        return len(self._variable_names)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """Return the number of columns in the model"""
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Optional[str]:
        if not index.isValid() or index.row() >= len(self._variable_names):
            return None

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return self._formula_names[index.row()]
            elif index.column() == 1:
                return self._variable_names[index.row()]

        return None

    def headerData(
        self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole
    ) -> Optional[str]:
        """Return the header data for the given section"""
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._headers[section]
        return None

    def get_variable_mapping(self) -> Dict[str, str]:
        """Get a dictionary mapping formula names to variable names"""
        return {
            formula_name: var_name
            for formula_name, var_name in zip(self._formula_names, self._variable_names)
        }


class FormulaEditor(QDialog):
    """Formula Dialog - provides a UI for inputting a formula with variables from a table."""

    formula_accepted = Signal(tuple)

    def __init__(self, parent: QObject, variable_names: List[str]) -> None:
        """
        Initialize the dialog

        Parameters:
        -----------
        parent : QObject
            Parent widget
        variable_names : List[str]
            List of variable names
        """
        super().__init__(parent)
        self.setWindowTitle("Formula Input")

        layout = QVBoxLayout(self)
        self.name_field = QLineEdit(self)
        self.field = QLineEdit(self)

        self.name_field.textChanged.connect(self.on_name_field_changed)

        self.variable_model = VariableModel(variable_names)
        self.variable_list = QTableView(self)
        self.variable_list.setModel(self.variable_model)
        self.variable_list.setEditTriggers(QAbstractItemView.EditTriggers(0))
        self.variable_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.variable_list.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.variable_list.setAlternatingRowColors(True)
        self.variable_list.setStyleSheet("alternate-background-color: #262E38;")
        self.variable_list.setMaximumWidth(1000)
        self.variable_list.setMaximumHeight(1000)

        header = self.variable_list.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.variable_list.verticalHeader().setVisible(False)

        layout_h = QHBoxLayout()
        layout_h.addWidget(QLabel("Formula Name"))
        layout_h.addWidget(self.name_field)

        layout.addWidget(self.variable_list)
        layout.addLayout(layout_h)
        layout.addWidget(self.field)

        self.variable_list.doubleClicked.connect(self.insert_variable)

        # Define the list of calculator buttons
        # fmt: off
        buttons = [
            "7",   "8",      "9",      "+",       "(",      ")",
            "4",   "5",      "6",      "-",       "^2",     "sqrt",
            "1",   "2",      "3",      "*",       "^-1",    "ln",
            "0",   "e",      "pi",     "/",       "sin",  "asin",
            ".",   "abs",  "min",  "^",       "cos",  "acos",
            "Clear",  "max",  "mean",  "tan",  "atan",
        ]

        button_to_formula = {
            "7": "7", "8": "8", "9": "9", "+": "+", "(": "(", ")": ")",
            "4": "4", "5": "5", "6": "6", "-": "-", "^2": "^2", "sqrt": "sqrt()",
            "1": "1", "2": "2", "3": "3", "*": "*", "^-1": "^-1", "ln": "ln()",
            "0": "0", "e": "e", "pi": "pi", "/": "/", "sin": "sin()", "asin": "asin()",
            ".": ".", "abs": "abs()", "min": "min()", "^": "^", "cos": "cos()", "acos": "acos()",
            "Clear": "", "max": "max()", "mean": "mean()", "tan": "tan()", "atan": "atan()",
        }

        # fmt: on

        grid_layout = QGridLayout()
        for i, button_text in enumerate(buttons):
            button = QPushButton(button_text, self)
            button.setFixedWidth(42)  # Set a fixed size for buttons
            row = i // 6
            col = i % 6
            grid_layout.addWidget(button, row, col)

            if button_text == "Clear":
                button.setStyleSheet(stylesheet_clear)
                button.clicked.connect(lambda _: self.field.clear())
            else:
                button.clicked.connect(
                    lambda _, text=button_text: self.field.insert(
                        button_to_formula[text]
                    )
                )

        layout.addLayout(grid_layout)

        ok_button = QPushButton("Add Formula", self)
        ok_button.setFixedHeight(32)
        ok_button.setStyleSheet(stylesheet_add)
        ok_button.clicked.connect(self.accept_formula)
        layout.addWidget(ok_button)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        """Handle key press events - submit on Enter/Return"""
        if e.key() == Qt.Key_Return or e.key() == Qt.Key_Enter:
            self.accept_formula()
        return super().keyPressEvent(e)

    @Slot()
    def accept_formula(self) -> None:
        """Process and emit the entered formula with variable mapping"""
        formula_name = self.name_field.text().strip()

        if not formula_name:
            self.name_field.setStyleSheet("QLineEdit { border: 2px solid red; }")
            self.name_field.setFocus()
            return

        formula_name = self.name_field.text()
        formula = self.field.text()
        formula = re.sub(r"\s+", "", formula)
        variable_mapping = self.variable_model.get_variable_mapping()

        self.formula_accepted.emit((formula_name, formula, variable_mapping))
        self.field.setText("")
        self.name_field.setText("")
        self.accept()

    @Slot(QModelIndex)
    def insert_variable(self, index: QModelIndex) -> None:
        """Insert the formula name into the formula field when a row is double-clicked"""
        if not index.isValid():
            return

        row = index.row()
        if row < 0 or row >= self.variable_model.rowCount():
            return

        model_index = self.variable_model.index(row, 0)
        formula_name = self.variable_model.data(model_index, Qt.DisplayRole)

        if formula_name:
            current_text = self.field.text()
            cursor_pos = self.field.cursorPosition()
            new_text = (
                current_text[:cursor_pos] + formula_name + current_text[cursor_pos:]
            )
            self.field.setText(new_text)
            self.field.setCursorPosition(cursor_pos + len(formula_name) + 2)

    def set_variable_names(self, variable_names: List[str]) -> None:
        """Set the variable names

        Parameters:
        -----------
        variable_names : List[str]
            List of variable names
        """
        self.variable_model.set_variable_names(variable_names)

    @Slot(str)
    def on_name_field_changed(self, text: str) -> None:
        """Remove red outline when text is added to name field"""
        if text.strip():
            self.name_field.setStyleSheet("")
