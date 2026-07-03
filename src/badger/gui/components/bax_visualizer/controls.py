"""Controls widget for the BAX visualizer.

This module provides the ControlsWidget class which manages the UI controls
for variable selection and visualization updates in the BAX visualizer.
"""

from typing import TYPE_CHECKING, Optional

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
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

        controls_layout.addWidget(self._create_variable_group())
        controls_layout.addWidget(self._create_plot_options())
        controls_layout.addStretch()  # Add stretch to push controls to the top

        # Add the controls to the layout

        self.update_button = self._create_update_button()

        # Add the controls to the layout

        controls_layout.addWidget(self.update_button)

        self.setLayout(controls_layout)

    def _create_plot_options(self) -> QGroupBox:
        layout = QVBoxLayout()
        group_widget = QGroupBox("Optional Plots")

        n_grid_label = QLabel("Number of Grid Points:")
        self.n_grid_spin_box = QSpinBox()
        self.n_grid_spin_box.setRange(10, 100)
        self.n_grid_spin_box.setSingleStep(10)
        self.n_grid_spin_box.setValue(self.parameters.tab_1.n_grid)

        n_samples_label = QLabel("Number of Samples:")
        self.n_samples_spin_box = QSpinBox()
        self.n_samples_spin_box.setRange(10, 100)
        self.n_samples_spin_box.setSingleStep(10)
        self.n_samples_spin_box.setValue(self.parameters.tab_1.n_samples)

        layout.addWidget(n_grid_label)
        layout.addWidget(self.n_grid_spin_box)
        layout.addWidget(n_samples_label)
        layout.addWidget(self.n_samples_spin_box)

        # Create checkboxes for optional plots based on the parameters

        self.grid_optimize_checkbox = QCheckBox("Grid Optimize")
        self.grid_optimize_checkbox.setChecked(
            self.parameters.tab_1.grid_optimize.objective
        )
        self.emittance_x_checkbox = QCheckBox("Emittance X")
        self.emittance_x_checkbox.setChecked(
            self.parameters.tab_1.emittance.emittance_x
        )
        self.emittance_y_checkbox = QCheckBox("Emittance Y")
        self.emittance_y_checkbox.setChecked(
            self.parameters.tab_1.emittance.emittance_y
        )
        self.bmag_x_checkbox = QCheckBox("Bmag X")
        self.bmag_x_checkbox.setChecked(self.parameters.tab_1.emittance.bmag_x)
        self.bmag_y_checkbox = QCheckBox("Bmag Y")
        self.bmag_y_checkbox.setChecked(self.parameters.tab_1.emittance.bmag_y)
        self.alignment_x_checkbox = QCheckBox("Alignment X")
        self.alignment_x_checkbox.setChecked(
            self.parameters.tab_1.pathwise_solenoid_alignment.misalignment_x
        )
        self.alignment_y_checkbox = QCheckBox("Alignment Y")
        self.alignment_y_checkbox.setChecked(
            self.parameters.tab_1.pathwise_solenoid_alignment.misalignment_y
        )

        layout.addWidget(self.grid_optimize_checkbox)
        layout.addWidget(self.emittance_x_checkbox)
        layout.addWidget(self.emittance_y_checkbox)
        layout.addWidget(self.bmag_x_checkbox)
        layout.addWidget(self.bmag_y_checkbox)
        layout.addWidget(self.alignment_x_checkbox)
        layout.addWidget(self.alignment_y_checkbox)

        group_widget.setLayout(layout)
        return group_widget

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

    def _create_variable_group(self) -> QGroupBox:
        group_box = QGroupBox("Variable Selection")
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
        group_box.setLayout(layout)
        return group_box

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
