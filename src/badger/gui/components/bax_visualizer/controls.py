"""Controls widget for the BAX visualizer.

This module provides the ControlsWidget class which manages the UI controls
for variable selection and visualization updates in the BAX visualizer.
"""

from typing import TYPE_CHECKING, Optional

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from badger.routine import Routine
from badger.utils import BlockSignalsContext

if TYPE_CHECKING:
    from badger.gui.components.bax_visualizer.bax_widget import Parameters


class ControlsWidget(QWidget):
    def __init__(
        self,
        routine: Routine,
        parameters: "Parameters",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent=parent)
        self.routine = routine
        self.parameters = parameters

        self._initialize_ui()

    def _initialize_ui(self) -> None:
        # Create the layout for the controls
        controls_layout = QVBoxLayout()

        controls_layout.addLayout(self._create_variable_layout())

        # Add the controls to the layout

        self.update_button = self._create_update_button()

        # Add the controls to the layout

        controls_layout.addWidget(self.update_button)

        self.setLayout(controls_layout)

    def update_controls(self) -> None:
        self.update_variables()
        with BlockSignalsContext((self.x_axis_combo_box, self.y_axis_combo_box)):
            # Update the combo boxes and checkbox based on the current parameters
            self.x_axis_combo_box.setCurrentIndex(self.parameters.variable_idx_x)
            self.y_axis_combo_box.setCurrentIndex(self.parameters.variable_idx_y)
            self.y_axis_checkbox.setChecked(self.parameters.include_y)

    def update_variables(self) -> None:
        # Update the parameters with the current variable names
        self.parameters.variables = self.routine.vocs.variable_names

        with BlockSignalsContext((self.x_axis_combo_box, self.y_axis_combo_box)):
            # Update the combo boxes with the new variable names
            self.x_axis_combo_box.clear()
            self.x_axis_combo_box.addItems(self.parameters.variables)

            self.y_axis_combo_box.clear()
            self.y_axis_combo_box.addItems(self.parameters.variables)

    def _create_variable_layout(self) -> QVBoxLayout:
        layout = QVBoxLayout()
        x_axis_combo_box, self.x_axis_combo_box = self._create_variable_combo_box(
            is_x_axis=True
        )
        y_axis_combo_box, self.y_axis_combo_box = self._create_variable_combo_box(
            is_x_axis=False, disabled=not self.parameters.include_y
        )
        self.y_axis_checkbox = self._create_include_y_checkbox()

        layout.addLayout(x_axis_combo_box)
        layout.addLayout(y_axis_combo_box)
        layout.addWidget(self.y_axis_checkbox)
        return layout

    def _create_variable_combo_box(
        self, is_x_axis: bool = True, disabled: bool = False
    ) -> tuple[QHBoxLayout, QComboBox]:
        layout = QHBoxLayout()
        # Create a combo box for selecting variables
        combo_box = QComboBox()
        label = QLabel("Variable 1:" if is_x_axis else "Variable 2:")
        combo_box.addItems(self.parameters.variables)
        if is_x_axis:
            combo_box.setCurrentIndex(self.parameters.variable_idx_x)
        else:
            combo_box.setCurrentIndex(self.parameters.variable_idx_y)
        combo_box.setDisabled(disabled)

        layout.addWidget(label)
        layout.addWidget(combo_box)

        return layout, combo_box

    def _create_include_y_checkbox(self) -> QCheckBox:
        # Create a checkbox for including/excluding the second variable
        checkbox = QCheckBox("Include Variable 2")
        checkbox.setChecked(self.parameters.include_y)
        return checkbox

    def _create_update_button(self) -> QPushButton:
        # Create a button for updating the plots
        button = QPushButton("Update")  # Replace with actual button implementation
        return button
