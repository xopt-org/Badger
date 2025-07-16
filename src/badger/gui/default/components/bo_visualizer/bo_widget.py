from typing import Optional, cast
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QWidget,
    QVBoxLayout,
    QMessageBox,
    QTableWidgetItem,
)
from PyQt5.QtWidgets import QSizePolicy

from badger.gui.default.components.bo_visualizer.types import ConfigurableOptions
from badger.gui.default.components.extension_utilities import (
    BlockSignalsContext,
    HandledException,
    signal_logger,
    to_precision_float,
)
from badger.routine import Routine
from badger.utils import create_archive_run_filename

from xopt.generator import Generator
from badger.gui.default.components.bo_visualizer.ui_components import UIComponents
from badger.gui.default.components.bo_visualizer.plotting_area import PlottingArea
from PyQt5.QtCore import Qt
from xopt.generators.bayesian.bayesian_generator import BayesianGenerator
from badger.gui.default.components.analysis_widget import AnalysisWidget

import logging

logger = logging.getLogger(__name__)


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
    "variables": [],
    "reference_points": {},
    "reference_points_range": {},
    "include_variable_2": True,
}


class BOPlotWidget(AnalysisWidget):
    generator: BayesianGenerator
    parameters: ConfigurableOptions = DEFAULT_PARAMETERS

    def __init__(
        self, parent: Optional[QWidget] = None, routine: Optional[Routine] = None
    ):
        logger.debug("Initializing BOPlotWidget")
        super().__init__(parent)

        self.create_ui()

        ExpandingPolicy = QSizePolicy.Policy.Expanding

        self.setSizePolicy(ExpandingPolicy, ExpandingPolicy)
        self.setMinimumSize(1250, 720)

    def isValidRoutine(self, routine: Routine) -> None:
        pass

    def create_ui(self) -> None:
        self.ui_components = UIComponents(self.parameters)
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

    def initialize_widget(self) -> None:
        logger.debug("Initializing plot with routine")
        logger.debug("Update vocs in UI components")

        variable_names = self.routine.vocs.variable_names
        self.parameters["variables"] = variable_names

        vocs_variables = cast(
            dict[str, tuple[float, float]],
            self.routine.vocs.variables,  # type: ignore
        )

        self.ui_components.initialize_variables(self.parameters, vocs_variables)

        self.ui_components.update_variables(self.parameters)

        vocs_variables = cast(
            dict[str, tuple[float, float]],
            self.routine.vocs.variables,  # type: ignore
        )
        # Initialize UI Components
        self.ui_components.initialize_ui_components(
            self.parameters,
        )

    def setup_connections(self) -> None:
        self.ui_components.update_button.clicked.connect(
            lambda: signal_logger("Update button clicked")(
                lambda: self.on_button_clicked()
            )()
        )

        # Similarly for other signals

        self.ui_components.x_axis_combo.currentIndexChanged.connect(
            lambda: signal_logger("Updated 'x_axis_combo'")(
                lambda: self.on_axis_selection_changed()
            )()
        )

        self.ui_components.y_axis_combo.currentIndexChanged.connect(
            lambda: signal_logger("Updated 'y_axis_combo'")(
                lambda: self.on_axis_selection_changed()
            )()
        )

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

            checkbox.stateChanged.connect(
                lambda: signal_logger("Updated checkbox")(
                    lambda: self.on_plot_options_changed()
                )()
            )

        # No. of Grid Points

        self.ui_components.n_grid.valueChanged.connect(
            lambda: signal_logger("Updated 'n_grid' spinbox")(
                lambda: self.on_plot_options_changed()
            )()
        )

        # Reference inputs

        if self.ui_components.reference_table is not None:
            self.ui_components.reference_table.cellChanged.connect(
                lambda: signal_logger("Updated 'reference_table'")(
                    lambda: self.on_reference_points_changed()
                )()
            )

        self.ui_components.set_best_reference_point_button.clicked.connect(
            lambda: signal_logger("Set best reference points clicked")(
                lambda: self.on_set_best_reference_point_clicked()
            )()
        )

    def on_button_clicked(self) -> None:
        self.update_extension(self.routine, True)

    def on_set_best_reference_point_clicked(self) -> None:
        logger.debug("Setting best reference points")
        try:
            self.set_best_reference_points()
        except Exception as e:
            logger.error(f"Error getting best reference points: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Error getting best reference points: {e}",
            )
        self.update_plots(requires_rebuild=True)

    def on_plot_options_changed(self) -> None:
        self.update_plots(requires_rebuild=True)

    def on_reference_points_changed(self) -> None:
        # Update the reference points in the plot

        self.parameters["reference_points"] = self.get_reference_points(
            self.ui_components.ref_inputs,
            self.parameters["variables"],
        )

        self.update_plots(requires_rebuild=True)

    def reset_widget(self) -> None:
        """
        Reset the components of the BOPlotWidget.
        This method should be called when the routine is changed or when the widget needs to be reset.
        """
        logger.debug("Resetting components of BOPlotWidget")
        self.ui_components.best_point_display.setText("")

    def requires_reinitialization(self) -> bool:
        # Check if the extension needs to be reinitialized
        logger.debug("Checking if BO Visualizer needs to be reinitialized")

        archive_name = create_archive_run_filename(self.routine)

        logger.debug(f"Archive name: {archive_name}")

        if not self.initialized:
            logger.debug("Reset - Extension never initialized")
            # Set up connections
            logger.debug("Setting up connections")
            self.setup_connections()
            self.routine_identifier = archive_name
            self.initialized = True
            return True

        if self.routine_identifier != archive_name:
            logger.debug("Reset - Routine name has changed")
            self.routine_identifier = archive_name
            self.reset_widget()
            return True

        if self.routine.data is None:
            logger.debug("Reset - No data available")

            return True

        previous_len = self.df_length
        self.df_length = len(self.routine.data)
        new_length = self.df_length

        if previous_len > new_length:
            logger.debug("Reset - Data length is the same or smaller")
            self.df_length = float("inf")
            return True

        return False

    def on_axis_selection_changed(self):
        logger.debug("Axis selection changed")

        selected_variables: list[str] = []

        previous_selected_options = (
            self.parameters["variable_1"],
            self.parameters["variable_2"],
            self.parameters["include_variable_2"],
        )

        x_var_index = self.ui_components.x_axis_combo.currentIndex()
        self.parameters["variable_1"] = x_var_index

        include_var2 = self.ui_components.y_axis_checkbox.isChecked()
        self.parameters["include_variable_2"] = include_var2
        if not include_var2:
            # Disable the y-axis combo box if variable 2 is not included
            self.ui_components.y_axis_combo.setEnabled(False)
        else:
            self.ui_components.y_axis_combo.setEnabled(True)
            y_var_index = self.ui_components.y_axis_combo.currentIndex()
            self.parameters["variable_2"] = y_var_index

        current_selected_options = (
            self.parameters["variable_1"],
            self.parameters["variable_2"],
            self.parameters["include_variable_2"],
        )

        logger.debug(f"previous_selected_options: {previous_selected_options}")
        logger.debug(f"current_selected_options: {current_selected_options}")

        # Update the selected variables based on the selected indices
        self.selected_variables = list(set(selected_variables))

        self.ui_components.x_axis_combo.setCurrentIndex(self.parameters["variable_1"])
        self.ui_components.y_axis_combo.setCurrentIndex(self.parameters["variable_2"])

        if previous_selected_options != current_selected_options:
            logger.debug("Selected variables for plotting:", self.selected_variables)
            # Update the reference point table based on the selected variables
            if self.ui_components.reference_table is not None:
                with BlockSignalsContext(
                    self.ui_components.reference_table,
                ):
                    self.update_reference_point_table(self.selected_variables)
            # Only update plot if the selection has changed
            self.update_plots()

    def update_reference_point_table(self, selected_variables: list[str]):
        """Disable and gray out reference points for selected variables."""

        for i, var_name in enumerate(self.parameters["variables"]):
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

    def get_reference_points(
        self, ref_inputs: list[QTableWidgetItem], variable_names: list[str]
    ):
        reference_points: dict[str, float] = {}

        # Create a mapping from variable names to ref_inputs
        ref_inputs_dict = dict(zip(self.parameters["variables"], ref_inputs))
        for var in self.parameters["variables"]:
            if var in variable_names:
                ref_value = float(ref_inputs_dict[var].text())
                reference_points[var] = ref_value
        return reference_points

    def update_plots(
        self,
        requires_rebuild: bool = False,
        interval: int = 1000,
    ) -> None:
        logger.debug("Updating plot in BOPlotWidget")

        selected_variables = [
            self.parameters["variables"][self.parameters["variable_1"]],
        ]

        if self.ui_components.y_axis_checkbox.isChecked():
            selected_variables.append(
                self.parameters["variables"][self.parameters["variable_2"]]
            )

        n_grid_value = self.ui_components.n_grid.value()

        if n_grid_value < self.parameters["plot_options"]["n_grid_range"][0]:
            logger.error(
                f"Number of grid points is less than the minimum value: {n_grid_value}"
            )
            return

        # Update the plot options
        self.parameters["plot_options"]["n_grid"] = self.ui_components.n_grid.value()
        self.parameters["plot_options"]["show_samples"] = (
            self.ui_components.show_samples_checkbox.isChecked()
        )
        self.parameters["plot_options"]["show_prior_mean"] = (
            self.ui_components.show_prior_mean_checkbox.isChecked()
        )
        self.parameters["plot_options"]["show_feasibility"] = (
            self.ui_components.show_feasibility_checkbox.isChecked()
        )
        self.parameters["plot_options"]["show_acq_func"] = (
            self.ui_components.acq_func_checkbox.isChecked()
        )

        self.ui_components.update_variables(self.parameters)

        # Disable signals for the reference table to prevent updating the plot multiple times
        if self.ui_components.reference_table is not None:
            with BlockSignalsContext(
                self.ui_components.reference_table,
            ):
                # Disable and gray out the reference points for selected variables
                self.update_reference_point_table(selected_variables)

        # Get reference points for non-selected variables

        non_selected_variables = [
            var for var in self.parameters["variables"] if var not in selected_variables
        ]

        reference_point = self.get_reference_points(
            self.ui_components.ref_inputs, non_selected_variables
        )

        logger.debug("Updating plot with selected variables and reference points")

        # Update the plot with the selected variables and reference points
        self.plotting_area.update_plot(
            self.routine,
            self.generator,
            self.parameters,
            self.update_extension,
            selected_variables,
            reference_point,
            self.parameters["plot_options"]["show_acq_func"],
            self.parameters["plot_options"]["show_samples"],
            self.parameters["plot_options"]["show_prior_mean"],
            self.parameters["plot_options"]["show_feasibility"],
            self.parameters["plot_options"]["n_grid"],
            requires_rebuild,
            interval,
        )

    def update_routine(self, routine: Routine, generator_type: type[Generator]) -> None:
        super().update_routine(routine, generator_type)

        # Handle the edge case where the extension has been opened after an optimization has already finished.
        if self.generator.model is None:
            logger.warning("Model not found in generator")

            try:
                if self.routine.data is None:
                    raise HandledException(
                        ValueError, "No data available in routine for training model"
                    )
                self.generator.train_model(self.routine.data)
            except HandledException as he:
                logger.error(str(he))
                raise he
            except Exception as e:
                logger.error(str(e))
                raise e

    def set_best_reference_points(
        self,
    ):
        if self.generator.data is None:
            raise HandledException(
                ValueError,
                "No data available in generator for selecting best reference points",
            )

        index_arr, value_arr, input_params = self.routine.vocs.select_best(
            self.generator.data
        )

        if not index_arr or not value_arr:
            raise HandledException(ValueError, "No best reference points found")

        if len(index_arr) < 1 or len(value_arr) < 1:
            raise HandledException(ValueError, "Best reference points arrays are empty")

        index = index_arr[0]
        value = value_arr[0]

        logger.debug(f"Best reference points index: {index}, value: {value}")
        logger.debug(f"Best reference points: {input_params}")

        # Update the reference table with the best reference points
        self.parameters["reference_points"] = cast(
            dict[str, float],
            {var: to_precision_float(input_params[var]) for var in input_params},
        )
        self.ui_components.best_point_display.setText(
            f"Best Point Index: {index}\nValue: {to_precision_float(value)}"
        )
