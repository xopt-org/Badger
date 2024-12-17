from typing import Optional
from PyQt5.QtWidgets import QHBoxLayout, QWidget, QVBoxLayout, QMessageBox

from badger.routine import Routine
from .ui_components import UIComponents
from .plotting_area import PlottingArea
from .model_logic import ModelLogic
from PyQt5.QtCore import Qt

import logging

logger = logging.getLogger(__name__)


class BOPlotWidget(QWidget):
    def __init__(
        self, parent: Optional[QWidget] = None, xopt_obj: Optional[Routine] = None
    ):
        logger.debug("Initializing BOPlotWidget")
        super().__init__(parent)
        self.selected_variables: list[str] = []  # Initialize selected_variables

        # Initialize model logic and UI components with None or default values
        self.model_logic = ModelLogic(xopt_obj, xopt_obj.vocs if xopt_obj else None)
        self.ui_components = UIComponents(xopt_obj.vocs if xopt_obj else None)
        self.plotting_area = PlottingArea()

        main_layout = QHBoxLayout(self)
        controls_layout = QVBoxLayout()

        # Initialize variable checkboxes (if needed)
        self.ui_components.initialize_variable_checkboxes(
            self.on_axis_selection_changed
        )

        controls_layout.addLayout(self.ui_components.create_axis_layout())
        controls_layout.addWidget(self.ui_components.create_reference_inputs())
        controls_layout.addWidget(self.ui_components.create_options_section())
        controls_layout.addLayout(self.ui_components.create_buttons())

        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.plotting_area, stretch=1)

        self.setLayout(main_layout)

        self.setSizePolicy(self.sizePolicy().Expanding, self.sizePolicy().Expanding)
        self.resize(1250, 720)

    def initialize_widget(self, xopt_obj: Routine):
        logger.debug("Initializing plot with xopt_obj")
        self.model_logic.update_xopt(xopt_obj)
        logger.debug("Update vocs in UI components")
        self.ui_components.update_vocs(xopt_obj.vocs, self.on_axis_selection_changed)

        # Set default selections for X-axis and Y-axis dropdowns
        self.ui_components.x_axis_combo.setCurrentIndex(0)  # Default to first variable
        self.ui_components.y_axis_combo.setCurrentIndex(1)  # Default to second variable

        # Set up connections
        logger.debug("Setting up connections")
        self.setup_connections()

        # Trigger the axis selection changed to disable reference points for default selected variables
        logger.debug("Triggering axis selection changed")
        self.on_axis_selection_changed()

        # # Now it's safe to call update_plot
        # logger.debug("Calling update_plot")
        # self.update_plot()

    def setup_connections(self):
        # Disconnect existing connections
        try:
            self.ui_components.update_button.clicked.disconnect()
        except TypeError:
            pass  # No connection to disconnect

        self.ui_components.update_button.clicked.connect(lambda: self.update_plot())

        # Similarly for other signals
        try:
            self.ui_components.x_axis_combo.currentIndexChanged.disconnect()
        except TypeError:
            pass
        self.ui_components.x_axis_combo.currentIndexChanged.connect(
            self.on_axis_selection_changed
        )

        try:
            self.ui_components.y_axis_combo.currentIndexChanged.disconnect()
        except TypeError:
            pass
        self.ui_components.y_axis_combo.currentIndexChanged.connect(
            self.on_axis_selection_changed
        )

        try:
            self.ui_components.y_axis_checkbox.stateChanged.disconnect()
        except TypeError:
            pass
        self.ui_components.y_axis_checkbox.stateChanged.connect(
            self.on_axis_selection_changed
        )

        # If you have variable checkboxes
        for checkbox in self.ui_components.variable_checkboxes.values():
            logger.debug(f"Setting up connection for checkbox: {checkbox.text()}")
            try:
                checkbox.stateChanged.disconnect()
            except TypeError:
                pass
            checkbox.stateChanged.connect(self.on_axis_selection_changed)

        # Plot options
        plot_options_checkboxes = [
            self.ui_components.acq_func_checkbox,
            self.ui_components.show_samples_checkbox,
            self.ui_components.show_prior_mean_checkbox,
            self.ui_components.show_feasibility_checkbox,
        ]

        for checkbox in plot_options_checkboxes:
            logger.debug(f"Setting up connection for checkbox: {checkbox.text()}")
            try:
                checkbox.stateChanged.disconnect()
            except TypeError:
                pass
            checkbox.stateChanged.connect(self.update_plot)

        # No. of Grid Points
        try:
            self.ui_components.n_grid.valueChanged.disconnect()
        except TypeError:
            pass
        self.ui_components.n_grid.valueChanged.connect(self.update_plot)

        # # Reference inputs
        # try:
        #     self.ui_components.reference_table.itemChanged.disconnect()
        # except TypeError:
        #     pass
        # self.ui_components.reference_table.itemChanged.connect(self.update_plot)

    def on_axis_selection_changed(self):
        if not self.model_logic.vocs or not self.ui_components.ref_inputs:
            # vocs or ref_inputs is not yet set; skip processing
            return

        logger.debug("Axis selection changed")

        previous_selected_variables = self.selected_variables.copy()

        # Start with an empty list of selected variables
        self.selected_variables = []

        # Always include X-axis variable
        x_var = self.ui_components.x_axis_combo.currentText()
        if x_var:
            self.selected_variables.append(x_var)

        # Include Y-axis variable only if the checkbox is checked
        if self.ui_components.y_axis_checkbox.isChecked():
            y_var = self.ui_components.y_axis_combo.currentText()
            if y_var and y_var != x_var:
                self.selected_variables.append(y_var)

        if len(self.selected_variables) == 0:
            # No variables selected; do not proceed with updating the plot
            logger.debug("No variables selected; skipping plot update")
            return

        if previous_selected_variables != self.selected_variables:
            print("Selected variables for plotting:", self.selected_variables)
            # Update the reference point table based on the selected variables
            self.update_reference_point_table(self.selected_variables)
            # Only update plot if the selection has changed
            self.update_plot()

    def update_plot(
        self, interval: Optional[float] = None, requires_rebuild: bool = False
    ):
        logger.debug("Updating plot in BOPlotWidget")
        if not self.model_logic.xopt_obj or not self.model_logic.vocs:
            print("Cannot update plot: xopt_obj or vocs is not available.")
            return

        # Ensure selected_variables is not empty
        if len(self.selected_variables) == 0:
            QMessageBox.warning(
                self,
                "No Variables Selected",
                "Please select at least one variable to plot.",
            )
            return

        # **Add validation for the number of variables**
        if len(self.selected_variables) > 2:
            QMessageBox.warning(
                self,
                "Too Many Variables Selected",
                "Visualization is only supported with respect to 1 or 2 variables. Please select up to 2 variables.",
            )
            return

        # Proceed with updating the plot
        selected_variables = self.selected_variables.copy()

        # Disable and gray out the reference points for selected variables
        self.update_reference_point_table(selected_variables)

        # Get reference points for non-selected variables
        reference_point = self.model_logic.get_reference_points(
            self.ui_components.ref_inputs, selected_variables
        )

        logger.debug("Updating plot with selected variables and reference points")

        # Update the plot with the selected variables and reference points
        return self.plotting_area.update_plot(
            self.model_logic.xopt_obj,
            selected_variables,
            reference_point,
            self.ui_components.acq_func_checkbox.isChecked(),
            self.ui_components.show_samples_checkbox.isChecked(),
            self.ui_components.show_prior_mean_checkbox.isChecked(),
            self.ui_components.show_feasibility_checkbox.isChecked(),
            self.ui_components.n_grid.value(),
            requires_rebuild,
            interval,
        )

    def update_reference_point_table(self, selected_variables: list[str]):
        """Disable and gray out reference points for selected variables."""
        if not self.model_logic.vocs or not self.ui_components.ref_inputs:
            # vocs or ref_inputs is not yet set; skip processing
            return

        for i, var_name in enumerate(self.model_logic.vocs.variable_names):
            # Get the reference point item from the table
            ref_item = self.ui_components.ref_inputs[i]

            white = Qt.GlobalColor.white
            lightGray = Qt.GlobalColor.lightGray
            black = Qt.GlobalColor.black

            itemIsEditable = Qt.ItemFlag.ItemIsEditable

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
        if self.ui_components.reference_table is not None:
            viewport = self.ui_components.reference_table.viewport()
            if viewport is not None:
                viewport.update()
