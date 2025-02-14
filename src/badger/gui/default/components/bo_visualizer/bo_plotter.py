from functools import wraps
from typing import Callable, Optional, ParamSpec, cast
from PyQt5.QtWidgets import QHBoxLayout, QWidget, QVBoxLayout
from PyQt5.QtWidgets import QSizePolicy

from badger.gui.default.components.bo_visualizer.types import ConfigurableOptions
from badger.routine import Routine
from .ui_components import UIComponents
from .plotting_area import PlottingArea
from .model_logic import ModelLogic
from PyQt5.QtCore import Qt
from xopt.generators.bayesian.bayesian_generator import BayesianGenerator

import logging

logger = logging.getLogger(__name__)

Param = ParamSpec("Param")


def signal_logger(text: str):
    def decorator(fn: Callable[Param, None]) -> Callable[Param, None]:
        @wraps(fn)
        def wrapper(*args: Param.args, **kwargs: Param.kwargs):
            logger.debug(f"{text}")
            return fn(*args, **kwargs)

        return wrapper

    return decorator


DEFAULT_PARAMETERS: ConfigurableOptions = {
    "plot_options": {
        "n_grid": 50,
        "n_grid_range": (10, 100),
        "show_samples": True,
        "show_prior_mean": False,
        "show_feasibility": False,
        "show_acq_func": True,
    },
    "variable_1": 0,
    "variable_2": 1,
    "include_variable_2": True,
}


class BOPlotWidget(QWidget):
    config_parameters: ConfigurableOptions

    def __init__(
        self, parent: Optional[QWidget] = None, routine: Optional[Routine] = None
    ):
        logger.debug("Initializing BOPlotWidget")
        super().__init__(parent)

        # Set default configuration parameters
        self.config_parameters = DEFAULT_PARAMETERS

        self.selected_variables: list[str] = []  # Initialize selected_variables

        # Initialize model logic and UI components with None or default values
        self.model_logic = ModelLogic(routine, routine.vocs if routine else None)
        self.ui_components = UIComponents(
            self.config_parameters, routine.vocs if routine else None
        )
        self.plotting_area = PlottingArea()

        main_layout = QHBoxLayout(self)
        controls_layout = QVBoxLayout()

        controls_layout.addLayout(self.ui_components.create_axis_layout())
        controls_layout.addWidget(self.ui_components.create_reference_inputs())
        controls_layout.addWidget(self.ui_components.create_options_section())
        controls_layout.addLayout(self.ui_components.create_buttons())

        main_layout.addLayout(controls_layout)
        main_layout.addWidget(self.plotting_area, stretch=1)

        self.setLayout(main_layout)

        ExpandingPolicy = QSizePolicy.Policy.Expanding

        self.setSizePolicy(ExpandingPolicy, ExpandingPolicy)
        self.setMinimumSize(1250, 720)

    def initialize_widget(
        self, routine: Routine, update_routine: Callable[[Routine], None]
    ) -> None:
        logger.debug("Initializing plot with routine")
        self.model_logic.update_routine(routine)
        logger.debug("Update vocs in UI components")
        self.ui_components.update_vocs(routine.vocs)
        self.ui_components.update_variables(self.config_parameters)

        # Set up connections
        logger.debug("Setting up connections")
        self.setup_connections(routine, update_routine)

        # Initialize UI Components
        self.ui_components.initialize_ui_components(self.config_parameters)

        # Trigger the axis selection changed to disable reference points for default selected variables
        logger.debug("Triggering axis selection changed")
        self.on_axis_selection_changed()

    def setup_connections(
        self, routine: Routine, update_routine: Callable[[Routine], None]
    ) -> None:
        # Disconnect existing connections
        try:
            self.ui_components.update_button.clicked.disconnect()
        except TypeError:
            pass  # No connection to disconnect

        self.ui_components.update_button.clicked.connect(
            lambda: signal_logger("Update button clicked")(
                lambda: update_routine(routine)
            )()
        )

        # Similarly for other signals
        try:
            self.ui_components.x_axis_combo.currentIndexChanged.disconnect()
        except TypeError:
            pass
        self.ui_components.x_axis_combo.currentIndexChanged.connect(
            lambda: signal_logger("Updated 'x_axis_combo'")(
                lambda: self.on_axis_selection_changed()
            )()
        )

        try:
            self.ui_components.y_axis_combo.currentIndexChanged.disconnect()
        except TypeError:
            pass
        self.ui_components.y_axis_combo.currentIndexChanged.connect(
            lambda: signal_logger("Updated 'y_axis_combo'")(
                lambda: self.on_axis_selection_changed()
            )()
        )

        try:
            self.ui_components.y_axis_checkbox.stateChanged.disconnect()
        except TypeError:
            pass
        self.ui_components.y_axis_checkbox.stateChanged.connect(
            lambda: signal_logger("Updated 'y_axis_checkbox'")(
                lambda: self.on_axis_selection_changed()
            )()
        )

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
            checkbox.stateChanged.connect(
                lambda: signal_logger("Updated checkbox")(lambda: self.update_plot())()
            )

        # No. of Grid Points
        try:
            self.ui_components.n_grid.valueChanged.disconnect()
        except TypeError:
            pass
        self.ui_components.n_grid.valueChanged.connect(
            lambda: signal_logger("Updated 'n_grid' spinbox")(
                lambda: self.update_plot()
            )()
        )

        # Reference inputs

        if self.ui_components.reference_table is not None:
            try:
                self.ui_components.reference_table.cellChanged.disconnect()
            except TypeError:
                pass
            self.ui_components.reference_table.cellChanged.connect(
                lambda: signal_logger("Updated 'reference_table'")(
                    lambda: self.update_plot()
                )()
            )

    def on_axis_selection_changed(self):
        if not self.model_logic.vocs or not self.ui_components.ref_inputs:
            # vocs or ref_inputs is not yet set; skip processing
            return

        logger.debug("Axis selection changed")

        selected_variables: list[str] = []

        previous_selected_options = (
            self.config_parameters["variable_1"],
            self.config_parameters["variable_2"],
            self.config_parameters["include_variable_2"],
        )

        x_var_index = self.ui_components.x_axis_combo.currentIndex()
        self.config_parameters["variable_1"] = x_var_index
        x_var_text = self.ui_components.x_axis_combo.currentText()
        if x_var_text != "":
            selected_variables.append(x_var_text)

        include_var2 = self.ui_components.y_axis_checkbox.isChecked()
        self.config_parameters["include_variable_2"] = include_var2
        if include_var2:
            y_var_index = self.ui_components.y_axis_combo.currentIndex()
            self.config_parameters["variable_2"] = y_var_index
            y_var_text = self.ui_components.y_axis_combo.currentText()
            if y_var_text != "":
                selected_variables.append(y_var_text)

        current_selected_options = (
            self.config_parameters["variable_1"],
            self.config_parameters["variable_2"],
            self.config_parameters["include_variable_2"],
        )

        logger.debug(f"previous_selected_options: {previous_selected_options}")
        logger.debug(f"current_selected_options: {current_selected_options}")

        # Update the selected variables based on the selected indices
        self.selected_variables = list(set(selected_variables))

        self.ui_components.x_axis_combo.setCurrentIndex(
            self.config_parameters["variable_1"]
        )
        self.ui_components.y_axis_combo.setCurrentIndex(
            self.config_parameters["variable_2"]
        )

        if previous_selected_options != current_selected_options:
            print("Selected variables for plotting:", self.selected_variables)
            # Update the reference point table based on the selected variables
            if self.ui_components.reference_table is not None:
                self.ui_components.reference_table.blockSignals(True)
                self.update_reference_point_table(self.selected_variables)
                self.ui_components.reference_table.blockSignals(False)
            # Only update plot if the selection has changed
            self.update_plot()

    def update_plot(
        self, interval: Optional[float] = None, requires_rebuild: bool = False
    ) -> None:
        logger.debug("Updating plot in BOPlotWidget")
        if not self.model_logic.routine or not self.model_logic.vocs:
            print("Cannot update plot: routine or vocs are not available.")
            return

        # Ensure selected_variables is not empty
        if len(self.selected_variables) == 0:
            logger.error("No variables selected for plotting")
            return

        # **Add validation for the number of variables**
        if len(self.selected_variables) > 2:
            logger.error("Too many variables selected for plotting")
            return

        for var in self.selected_variables:
            if var == "":
                logger.error("Empty variable selected for plotting")
                return

        n_grid_value = self.ui_components.n_grid.value()

        if n_grid_value < self.config_parameters["plot_options"]["n_grid_range"][0]:
            logger.error(
                f"Number of grid points is less than the minimum value: {n_grid_value}"
            )
            return

        # Update the plot options
        self.config_parameters["plot_options"]["n_grid"] = (
            self.ui_components.n_grid.value()
        )
        self.config_parameters["plot_options"]["show_samples"] = (
            self.ui_components.show_samples_checkbox.isChecked()
        )
        self.config_parameters["plot_options"]["show_prior_mean"] = (
            self.ui_components.show_prior_mean_checkbox.isChecked()
        )
        self.config_parameters["plot_options"]["show_feasibility"] = (
            self.ui_components.show_feasibility_checkbox.isChecked()
        )
        self.config_parameters["plot_options"]["show_acq_func"] = (
            self.ui_components.acq_func_checkbox.isChecked()
        )

        # Disable signals for the reference table to prevent updating the plot multiple times
        if self.ui_components.reference_table is not None:
            self.ui_components.reference_table.blockSignals(True)

            # Disable and gray out the reference points for selected variables
            self.update_reference_point_table(self.selected_variables)

            self.ui_components.reference_table.blockSignals(False)

        # Get reference points for non-selected variables
        reference_point = self.model_logic.get_reference_points(
            self.ui_components.ref_inputs, self.selected_variables
        )
        generator = cast(BayesianGenerator, self.model_logic.routine.generator)

        logger.debug("Updating plot with selected variables and reference points")

        # Update the plot with the selected variables and reference points
        self.plotting_area.update_plot(
            generator,
            self.selected_variables,
            reference_point,
            self.config_parameters["plot_options"]["show_acq_func"],
            self.config_parameters["plot_options"]["show_samples"],
            self.config_parameters["plot_options"]["show_prior_mean"],
            self.config_parameters["plot_options"]["show_feasibility"],
            self.config_parameters["plot_options"]["n_grid"],
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
