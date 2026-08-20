"""Widget that hosts the BAX visualizer extension within the Badger GUI.

BAX (Bayesian Algorithm Execution) runs a virtual algorithm on samples drawn
from the generator's Gaussian-process model to decide where to measure next.
This widget visualizes that process, plotting the model's predictions and the
sampled algorithm executions so the user can see what BAX infers about the
target quantity (e.g. emittance or solenoid alignment) as the run progresses.
"""

import logging
import time
from dataclasses import dataclass, field

from PyQt5.QtWidgets import QSizePolicy, QVBoxLayout, QWidget
from xopt.generators.bayesian.bax_generator import BaxGenerator
from xopt.generators.bayesian.bayesian_generator import BayesianGenerator

from badger.gui.components.analysis_widget import AnalysisWidget
from badger.gui.components.bax_visualizer.ui import UI
from badger.gui.components.extension_utilities import (
    HandledException,
    get_latest_reference_points,
    requires_update,
)
from badger.routine import Routine
from badger.utils import BlockSignalsContext

logger = logging.getLogger(__name__)


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
    n_grid: int = 20
    n_samples: int = 100
    reference_points: dict[str, float] = field(default_factory=dict)
    objective: bool = True
    # grid_optimize: GridOptimizePlots = field(default_factory=GridOptimizePlots)
    pathwise_minimize_emittance: EmittancePlots = field(default_factory=EmittancePlots)
    pathwise_solenoid_alignment: PathwiseSolenoidAlignmentPlots = field(
        default_factory=PathwiseSolenoidAlignmentPlots
    )


# @dataclass()
# class Plot2Parameters:


@dataclass()
class Parameters:
    tab_1: Plot1Parameters = field(default_factory=Plot1Parameters)
    # tab_2: Plot2Parameters = field(default_factory=Plot2Parameters)
    active_tab: int = 0
    variables: list[str] = field(default_factory=list)
    variable_idx_x: int = 0
    variable_idx_y: int = 1
    include_y: bool = True


class BaxWidget(AnalysisWidget):
    generator: BaxGenerator
    parameters: Parameters  # type: ignore[assignment]

    def __init__(self, routine: Routine, parent: QWidget | None = None):
        logger.debug("Initializing BaxWidget")
        super().__init__(routine=routine, parent=parent)

        # Instance-level parameters. Never use a class-level default here: it
        # would be shared (and mutated) across every BaxWidget instance.
        self.parameters = Parameters()

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

        # Start from a clean parameter state and propagate that single object to
        # every child widget so the whole UI subtree resets in lock-step. Simply
        # rebinding ``self.parameters`` would leave the UI holding the previous
        # run's object and cause state to desync.
        self.parameters = Parameters()
        self.ui.set_parameters(self.parameters)

        # The child widgets also cache the routine/generator they were built
        # with. Refresh them too, otherwise the controls read the previous
        # routine's variables (leaving stale reference-point keys behind).
        self.ui.set_routine(self.routine)

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
        self.ui.reset_ui()

        self.ui.initialize_reference_table()

    def reset_widget(self) -> None:
        logger.debug("Resetting BaxWidget")
        self.routine_identifier = ""
        self.df_length = float("inf")
        self.ui.reset_ui()

    def update_plots(self, requires_rebuild: bool, interval: int) -> None:
        if not requires_update(self.last_updated, interval, requires_rebuild):
            return

        # The plotting area caches the generator it was built with. Re-sync it
        # with the current routine's generator so it reads this run's
        # algorithm_results_file instead of a stale one from a previous run.
        self.ui.plotting_area.generator = self.generator

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

        self.ui.controls_area.reference_table.cellChanged.connect(
            lambda: self.update_reference_point()
        )

        self.ui.controls_area.select_latest_reference_point_button.clicked.connect(
            lambda: self.set_latest_reference_points()
        )

        # Plotting options checkboxes
        for label, value in [
            ("Grid Optimize", self.parameters.tab_1.objective),
            (
                "Emittance X",
                self.parameters.tab_1.pathwise_minimize_emittance.emittance_x,
            ),
            (
                "Emittance Y",
                self.parameters.tab_1.pathwise_minimize_emittance.emittance_y,
            ),
            ("Bmag X", self.parameters.tab_1.pathwise_minimize_emittance.bmag_x),
            ("Bmag Y", self.parameters.tab_1.pathwise_minimize_emittance.bmag_y),
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

    def set_latest_reference_points(
        self,
    ) -> None:
        if self.generator.data is None:
            raise HandledException(
                ValueError,
                "No data available in generator for selecting latest reference points",
            )

        reference_points = get_latest_reference_points(
            self.generator.data, self.routine.vocs.variable_names
        )

        logger.debug(f"Latest reference points: {reference_points}")

        # Update the reference table with the latest reference points
        self.parameters.tab_1.reference_points = reference_points
        self.ui.controls_area.reference_point_display.setText(
            f"Latest Reference Points: {', '.join(f'{k}: {v}' for k, v in reference_points.items())}"
        )

        self.ui.controls_area.populate_reference_table()

        self.update_plots(requires_rebuild=True, interval=0)

    def update_reference_point(self) -> None:
        self.parameters.tab_1.reference_points = (
            self.ui.controls_area.get_reference_points(self.parameters.variables)
        )
        self.update_plots(requires_rebuild=True, interval=0)

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
            self.parameters.tab_1.objective = is_checked
        elif label == "Emittance X":
            self.parameters.tab_1.pathwise_minimize_emittance.emittance_x = is_checked
        elif label == "Emittance Y":
            self.parameters.tab_1.pathwise_minimize_emittance.emittance_y = is_checked
        elif label == "Bmag X":
            self.parameters.tab_1.pathwise_minimize_emittance.bmag_x = is_checked
        elif label == "Bmag Y":
            self.parameters.tab_1.pathwise_minimize_emittance.bmag_y = is_checked
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

        with BlockSignalsContext(self.ui.controls_area.reference_table):
            self.ui.controls_area.update_reference_point_table_editability()

        self.update_plots(requires_rebuild=True, interval=0)

    def update_y_axis_controls(self) -> None:

        self.parameters.include_y = self.ui.controls_area.y_axis_checkbox.isChecked()

        if not self.parameters.include_y:
            self.ui.controls_area.y_axis_combo_box.setEnabled(False)
        else:
            self.ui.controls_area.y_axis_combo_box.setEnabled(True)

        with BlockSignalsContext(self.ui.controls_area.reference_table):
            self.ui.controls_area.update_reference_point_table_editability()

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
