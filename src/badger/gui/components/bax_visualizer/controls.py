"""Controls widget for the BAX visualizer.

This module provides the ControlsWidget class which manages the UI controls
for variable selection and visualization updates in the BAX visualizer.
"""

from typing import TYPE_CHECKING, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from badger.routine import Routine
from badger.utils import BlockSignalsContext

if TYPE_CHECKING:
    from badger.gui.components.bax_visualizer.bax_widget import Parameters

import logging

logger = logging.getLogger(__name__)


class ControlsWidget(QWidget):
    ref_inputs: list[QTableWidgetItem] = []

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
        controls_layout.addWidget(self._create_reference_point_group())
        controls_layout.addWidget(self._create_plot_options())
        controls_layout.addStretch()  # Add stretch to push controls to the top

        # Add the controls to the layout

        self.update_button = self._create_update_button()

        # Add the controls to the layout

        controls_layout.addWidget(self.update_button)

        self.setLayout(controls_layout)

    def reset_controls_widget(self) -> None:
        """Reset the controls to their initial state."""

        with BlockSignalsContext(
            [
                self.emittance_x_checkbox,
                self.emittance_y_checkbox,
                self.bmag_x_checkbox,
                self.bmag_y_checkbox,
                self.alignment_x_checkbox,
                self.alignment_y_checkbox,
                self.grid_optimize_checkbox,
                self.n_grid_spin_box,
                self.n_samples_spin_box,
                self.y_axis_checkbox,
                self.reference_table,
                self.x_axis_combo_box,
                self.y_axis_combo_box,
            ]
        ):
            # Start from every option visible, then hide the ones that are not
            # relevant to the current algorithm. Resetting visibility first
            # ensures a checkbox hidden by a previous run's algorithm is shown
            # again when the routine changes.
            all_option_checkboxes = [
                self.grid_optimize_checkbox,
                self.emittance_x_checkbox,
                self.emittance_y_checkbox,
                self.bmag_x_checkbox,
                self.bmag_y_checkbox,
                self.alignment_x_checkbox,
                self.alignment_y_checkbox,
            ]
            for checkbox in all_option_checkboxes:
                checkbox.setVisible(True)

            # Hide plotting options that are not relevant to the current algorithm
            algorithm_type = self.routine.generator.algorithm.name
            if algorithm_type == "grid_optimize":
                self.emittance_x_checkbox.setVisible(False)
                self.emittance_y_checkbox.setVisible(False)
                self.bmag_x_checkbox.setVisible(False)
                self.bmag_y_checkbox.setVisible(False)
                self.alignment_x_checkbox.setVisible(False)
                self.alignment_y_checkbox.setVisible(False)
            elif algorithm_type == "pathwise_minimize_emittance":
                self.grid_optimize_checkbox.setVisible(False)
                self.alignment_x_checkbox.setVisible(False)
                self.alignment_y_checkbox.setVisible(False)
            elif algorithm_type == "pathwise_solenoid_alignment":
                self.grid_optimize_checkbox.setVisible(False)
                self.emittance_x_checkbox.setVisible(False)
                self.emittance_y_checkbox.setVisible(False)
                self.bmag_x_checkbox.setVisible(False)
                self.bmag_y_checkbox.setVisible(False)
            else:
                raise ValueError(f"Unsupported algorithm type: {algorithm_type}")

            # Push the (freshly reset) parameter values back into every widget so
            # no toggle, spin value or selection lingers from the previous run.
            self._sync_plot_options_from_parameters()

            self.reference_table.clearContents()

            self.x_axis_combo_box.clear()
            self.y_axis_combo_box.clear()

    def _sync_plot_options_from_parameters(self) -> None:
        """Set every plot-option widget to match the current parameters.

        Callers are responsible for blocking signals; this only mutates widget
        state to mirror ``self.parameters``.
        """
        tab = self.parameters.tab_1

        self.n_grid_spin_box.setValue(tab.n_grid)
        self.n_samples_spin_box.setValue(tab.n_samples)

        self.grid_optimize_checkbox.setChecked(tab.objective)
        self.emittance_x_checkbox.setChecked(
            tab.pathwise_minimize_emittance.emittance_x
        )
        self.emittance_y_checkbox.setChecked(
            tab.pathwise_minimize_emittance.emittance_y
        )
        self.bmag_x_checkbox.setChecked(tab.pathwise_minimize_emittance.bmag_x)
        self.bmag_y_checkbox.setChecked(tab.pathwise_minimize_emittance.bmag_y)
        self.alignment_x_checkbox.setChecked(
            tab.pathwise_solenoid_alignment.misalignment_x
        )
        self.alignment_y_checkbox.setChecked(
            tab.pathwise_solenoid_alignment.misalignment_y
        )
        self.y_axis_checkbox.setChecked(self.parameters.include_y)

    def _create_reference_point_group(self) -> QGroupBox:
        layout = QVBoxLayout()
        group_widget = QGroupBox("Reference Point")

        self.reference_table = QTableWidget()
        self.reference_table.setColumnCount(2)
        self.reference_table.setHorizontalHeaderLabels(["Variable", "Value"])
        horizontal_header = self.reference_table.horizontalHeader()
        horizontal_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        self.select_latest_reference_point_button = QPushButton("Set Latest")
        self.reference_point_display = QLabel("")

        layout.addWidget(self.reference_table)
        layout.addWidget(self.select_latest_reference_point_button)
        layout.addWidget(self.reference_point_display)

        group_widget.setLayout(layout)
        return group_widget

    def populate_reference_table(
        self,
    ) -> None:
        """Populate the reference table based on the current vocs variable names."""

        logger.debug("Populating reference table")

        with BlockSignalsContext(self.reference_table):
            self.reference_table.setRowCount(len(self.parameters.variables))
            self.ref_inputs: list[QTableWidgetItem] = []

            for i, var_name in enumerate(self.parameters.variables):
                variable_item = QTableWidgetItem(var_name)
                itemIsEditable = Qt.ItemFlag.ItemIsEditable

                variable_item.setFlags(
                    variable_item.flags() & ~Qt.ItemFlags(itemIsEditable)
                )
                self.reference_table.setItem(i, 0, variable_item)

                value = self.parameters.tab_1.reference_points[var_name]

                reference_point_item = QTableWidgetItem(str(value))
                self.ref_inputs.append(reference_point_item)
                self.reference_table.setItem(i, 1, reference_point_item)

            self.update_reference_point_table_editability()

    def get_reference_points(self, variable_names: list[str]) -> dict[str, float]:
        reference_points: dict[str, float] = {}

        # Create a mapping from variable names to ref_inputs
        ref_inputs_dict = dict(zip(self.parameters.variables, self.ref_inputs))
        for var in self.parameters.variables:
            if var in variable_names:
                ref_value = float(ref_inputs_dict[var].text())
                reference_points[var] = ref_value
        return reference_points

    def update_reference_point_table_editability(self) -> None:
        """Disable and gray out reference points for selected variables."""

        selected_variables = self.get_selected_variables()

        white = Qt.GlobalColor.white
        lightGray = Qt.GlobalColor.lightGray
        black = Qt.GlobalColor.black

        itemIsEditable = Qt.ItemFlag.ItemIsEditable

        for i, var_name in enumerate(self.parameters.variables):
            # Get the reference point item from the table
            ref_item = self.ref_inputs[i]

            if var_name in selected_variables:
                # Disable editing and gray out the background
                ref_item.setFlags(ref_item.flags() & ~Qt.ItemFlags(itemIsEditable))
                ref_item.setBackground(lightGray)
                ref_item.setForeground(white)
            else:
                # Re-enable editing and set background to white
                ref_item.setFlags(ref_item.flags() | Qt.ItemFlags(itemIsEditable))
                ref_item.setBackground(white)
                ref_item.setForeground(black)

        # Force the table to refresh and update its view
        viewport = self.reference_table.viewport()
        viewport.update()

    def get_selected_variables(self) -> list[str]:
        """Get the currently selected variables from the combo boxes."""
        selected_variables = [self.parameters.variables[self.parameters.variable_idx_x]]
        if self.parameters.include_y:
            selected_variables.append(
                self.parameters.variables[self.parameters.variable_idx_y]
            )
        return selected_variables

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
        self.n_samples_spin_box.setRange(10, 1000)
        self.n_samples_spin_box.setSingleStep(10)
        self.n_samples_spin_box.setValue(self.parameters.tab_1.n_samples)

        layout.addWidget(n_grid_label)
        layout.addWidget(self.n_grid_spin_box)
        layout.addWidget(n_samples_label)
        layout.addWidget(self.n_samples_spin_box)

        # Create checkboxes for optional plots based on the parameters

        self.grid_optimize_checkbox = QCheckBox("Show Objective")
        self.grid_optimize_checkbox.setChecked(self.parameters.tab_1.objective)
        self.emittance_x_checkbox = QCheckBox("Show Emittance X")
        self.emittance_x_checkbox.setChecked(
            self.parameters.tab_1.pathwise_minimize_emittance.emittance_x
        )
        self.emittance_y_checkbox = QCheckBox("Show Emittance Y")
        self.emittance_y_checkbox.setChecked(
            self.parameters.tab_1.pathwise_minimize_emittance.emittance_y
        )
        self.bmag_x_checkbox = QCheckBox("Show Bmag X")
        self.bmag_x_checkbox.setChecked(
            self.parameters.tab_1.pathwise_minimize_emittance.bmag_x
        )
        self.bmag_y_checkbox = QCheckBox("Show Bmag Y")
        self.bmag_y_checkbox.setChecked(
            self.parameters.tab_1.pathwise_minimize_emittance.bmag_y
        )
        self.alignment_x_checkbox = QCheckBox("Show Alignment X")
        self.alignment_x_checkbox.setChecked(
            self.parameters.tab_1.pathwise_solenoid_alignment.misalignment_x
        )
        self.alignment_y_checkbox = QCheckBox("Show Alignment Y")
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
        button = QPushButton("Update")
        return button
