"""Widget that hosts the BAX visualizer extension within the Badger GUI."""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from PyQt5.QtWidgets import QSizePolicy, QVBoxLayout, QWidget
from xopt.generators.bayesian.bax_generator import BaxGenerator
from xopt.generators.bayesian.bayesian_generator import BayesianGenerator

from badger.gui.components.analysis_widget import AnalysisWidget
from badger.gui.components.bax_visualizer.ui import UI
from badger.gui.components.extension_utilities import HandledException, requires_update
from badger.routine import Routine
from badger.utils import BlockSignalsContext, create_archive_run_filename

logger = logging.getLogger(__name__)


@dataclass
class GridOptimizePlots:
    objective: bool = True


@dataclass
class EmittancePlots:
    emittance_x: bool = True
    emittance_y: bool = True
    bmag_x: bool = True
    bmag_y: bool = True


@dataclass
class PathwiseSolenoidAlignmentPlots:
    misalignment_x: bool = True
    misalignment_y: bool = True


@dataclass()
class Plot1Parameters:
    n_grid: int = 50
    n_samples: int = 100
    grid_optimize: GridOptimizePlots = field(default_factory=GridOptimizePlots)
    emittance: EmittancePlots = field(default_factory=EmittancePlots)
    pathwise_solenoid_alignment: PathwiseSolenoidAlignmentPlots = field(
        default_factory=PathwiseSolenoidAlignmentPlots
    )


@dataclass()
class Plot2Parameters:
    n_grid: int = 50
    n_samples: int = 100


@dataclass()
class Parameters:
    tab_1: Plot1Parameters = field(default_factory=Plot1Parameters)
    tab_2: Plot2Parameters = field(default_factory=Plot2Parameters)
    active_tab: int = 0
    variables: list[str] = field(default_factory=list)
    variable_idx_x: int = 0
    variable_idx_y: int = 1
    include_y: bool = True


DEFAULT_PARAMETERS = Parameters()


class BaxWidget(AnalysisWidget):
    generator: BaxGenerator
    parameters: Parameters = DEFAULT_PARAMETERS

    def __init__(self, routine: Routine, parent: Optional[QWidget] = None):
        logger.debug("Initializing BaxWidget")
        super().__init__(routine=routine, parent=parent)

        self.ui = UI(routine=self.routine, parameters=self.parameters)

        # The UI must live inside a layout, otherwise Qt never manages its
        # geometry and the widget's size hints / minimum size are ignored.
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)
        self.setLayout(layout)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(800, 600)

        self.initialize_widget()

    def initialize_widget(self) -> None:
        logger.debug("Initializing BaxWidget")

        self.parameters = DEFAULT_PARAMETERS

        variable_names = list(self.routine.vocs.variable_names)
        self.parameters.variables = variable_names

        temp_x = self.parameters.variable_idx_x
        temp_y = self.parameters.variable_idx_y
        if len(variable_names) < 2:
            self.parameters.include_y = False
            self.parameters.variable_idx_x = 0
            self.parameters.variable_idx_y = -1
        else:
            self.parameters.include_y = True
            self.parameters.variable_idx_x = min(temp_x, len(variable_names) - 1)
            self.parameters.variable_idx_y = min(temp_y, len(variable_names) - 1)

        # Hide plotting options that are not relevant to the current algorithm
        algorithm_type = self.generator.algorithm.name
        if algorithm_type == "grid_optimize":
            self.ui.controls_area.emittance_x_checkbox.setVisible(False)
            self.ui.controls_area.emittance_y_checkbox.setVisible(False)
            self.ui.controls_area.bmag_x_checkbox.setVisible(False)
            self.ui.controls_area.bmag_y_checkbox.setVisible(False)
            self.ui.controls_area.alignment_x_checkbox.setVisible(False)
            self.ui.controls_area.alignment_y_checkbox.setVisible(False)
        elif algorithm_type == "emittance":
            self.ui.controls_area.grid_optimize_checkbox.setVisible(False)
            self.ui.controls_area.alignment_x_checkbox.setVisible(False)
            self.ui.controls_area.alignment_y_checkbox.setVisible(False)
        elif algorithm_type == "pathwise_solenoid_alignment":
            self.ui.controls_area.grid_optimize_checkbox.setVisible(False)
            self.ui.controls_area.emittance_x_checkbox.setVisible(False)
            self.ui.controls_area.emittance_y_checkbox.setVisible(False)

    def requires_reinitialization(self) -> bool:
        # Check if the extension needs to be reinitialized
        logger.debug("Checking if Bax Visualizer needs to be reinitialized")

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
            logger.debug("Reset - Data length is smaller")
            self.df_length = float("inf")
            return True

        return False

    def reset_widget(self) -> None:
        logger.debug("Resetting BaxWidget")
        self.routine_identifier = ""
        self.df_length = float("inf")

    def update_plots(self, requires_rebuild: bool, interval: int) -> None:
        if not requires_update(self.last_updated, interval, requires_rebuild):
            return

        # The plotting area caches the generator it was built with. Re-sync it
        # with the current routine's generator so it reads this run's
        # algorithm_results_file instead of a stale one from a previous run.
        self.ui.plotting_area.generator = self.generator

        self.ui.controls_area.update_controls()

        self.ui.plotting_area.update_tab_widget()

        self.last_updated = time.time()

    def setup_connections(self) -> None:
        self.ui.controls_area.update_button.clicked.connect(
            lambda: self.update_plots(requires_rebuild=True, interval=0)
        )

        self.ui.controls_area.x_axis_combo_box.currentIndexChanged.connect(
            lambda: self.update_variables()
        )
        self.ui.controls_area.y_axis_combo_box.currentIndexChanged.connect(
            lambda: self.update_variables()
        )
        self.ui.controls_area.y_axis_checkbox.stateChanged.connect(
            lambda: self.update_y_axis_controls()
        )
        self.ui.plotting_area.plot_tab_widget.currentChanged.connect(
            lambda index: self.update_tab_index(index)
        )

        self.ui.controls_area.n_grid_spin_box.valueChanged.connect(
            lambda value: self.update_n_grid(value)
        )
        self.ui.controls_area.n_samples_spin_box.valueChanged.connect(
            lambda value: self.update_n_samples(value)
        )

        # Plotting options checkboxes
        for label, value in [
            ("Grid Optimize", self.parameters.tab_1.grid_optimize.objective),
            ("Emittance X", self.parameters.tab_1.emittance.emittance_x),
            ("Emittance Y", self.parameters.tab_1.emittance.emittance_y),
            ("Bmag X", self.parameters.tab_1.emittance.bmag_x),
            ("Bmag Y", self.parameters.tab_1.emittance.bmag_y),
            (
                "Alignment X",
                self.parameters.tab_1.pathwise_solenoid_alignment.misalignment_x,
            ),
            (
                "Alignment Y",
                self.parameters.tab_1.pathwise_solenoid_alignment.misalignment_y,
            ),
        ]:
            checkbox = getattr(
                self.ui.controls_area, label.replace(" ", "_").lower() + "_checkbox"
            )
            checkbox.stateChanged.connect(
                lambda _, lbl=label: self.update_plot_option(lbl)
            )

    def update_n_grid(self, value: int) -> None:
        self.parameters.tab_1.n_grid = value
        self.update_plots(requires_rebuild=True, interval=0)

    def update_n_samples(self, value: int) -> None:
        self.parameters.tab_1.n_samples = value
        self.update_plots(requires_rebuild=True, interval=0)

    def update_plot_option(self, label: str) -> None:
        checkbox = getattr(
            self.ui.controls_area, label.replace(" ", "_").lower() + "_checkbox"
        )
        is_checked = checkbox.isChecked()

        if label == "Grid Optimize":
            self.parameters.tab_1.grid_optimize.objective = is_checked
        elif label == "Emittance X":
            self.parameters.tab_1.emittance.emittance_x = is_checked
        elif label == "Emittance Y":
            self.parameters.tab_1.emittance.emittance_y = is_checked
        elif label == "Bmag X":
            self.parameters.tab_1.emittance.bmag_x = is_checked
        elif label == "Bmag Y":
            self.parameters.tab_1.emittance.bmag_y = is_checked
        elif label == "Alignment X":
            self.parameters.tab_1.pathwise_solenoid_alignment.misalignment_x = (
                is_checked
            )
        elif label == "Alignment Y":
            self.parameters.tab_1.pathwise_solenoid_alignment.misalignment_y = (
                is_checked
            )

        self.update_plots(requires_rebuild=True, interval=0)

    def update_tab_index(self, index: int) -> None:
        self.parameters.active_tab = index

    def update_variables(self) -> None:

        previous_x_index = self.parameters.variable_idx_x
        previous_y_index = self.parameters.variable_idx_y

        current_x_index = self.ui.controls_area.x_axis_combo_box.currentIndex()
        current_y_index = self.ui.controls_area.y_axis_combo_box.currentIndex()

        if current_x_index == current_y_index:
            with BlockSignalsContext(
                (
                    self.ui.controls_area.x_axis_combo_box,
                    self.ui.controls_area.y_axis_combo_box,
                )
            ):
                # If the user selects the same variable for both axes, we can either swap the previous indices or reset to defaults. Here, we choose to swap.
                self.ui.controls_area.x_axis_combo_box.setCurrentIndex(previous_y_index)
                self.ui.controls_area.y_axis_combo_box.setCurrentIndex(previous_x_index)
            # If the user selects the same variable for both axes, we can either swap the previous indices or reset to defaults. Here, we choose to swap.
            current_x_index = self.parameters.variable_idx_y
            current_y_index = self.parameters.variable_idx_x

        self.parameters.variable_idx_x = current_x_index
        self.parameters.variable_idx_y = current_y_index

        self.update_plots(requires_rebuild=True, interval=0)

    def update_y_axis_controls(self) -> None:

        self.parameters.include_y = self.ui.controls_area.y_axis_checkbox.isChecked()

        if not self.parameters.include_y:
            self.ui.controls_area.y_axis_combo_box.setEnabled(False)
        else:
            self.ui.controls_area.y_axis_combo_box.setEnabled(True)

        self.update_plots(requires_rebuild=True, interval=0)

    def isValidRoutine(self, routine: Routine) -> None:
        if not isinstance(routine.generator, BayesianGenerator):
            raise HandledException(
                ValueError, "Bax Visualizer can only be used with a BayesianGenerator."
            )
        if len(routine.vocs.objective_names) > 0:
            raise HandledException(
                ValueError,
                "BAX Visualizer uses observations to visualize the optimization process, and therefore cannot be used with routines that have objectives defined. Please remove the objectives from your routine and try again.",
            )
