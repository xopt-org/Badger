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
from badger.utils import create_archive_run_filename

logger = logging.getLogger(__name__)


@dataclass()
class PlotParameters:
    n_grid: int = 50
    n_samples: int = 100


@dataclass()
class Parameters:
    tab_1: PlotParameters = field(default_factory=PlotParameters)
    tab_2: PlotParameters = field(default_factory=PlotParameters)
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

    def update_variables(self) -> None:

        self.parameters.variable_idx_x = (
            self.ui.controls_area.x_axis_combo_box.currentIndex()
        )
        self.parameters.variable_idx_y = (
            self.ui.controls_area.y_axis_combo_box.currentIndex()
        )

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
