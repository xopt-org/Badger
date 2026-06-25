"""Widget that hosts the BAX visualizer extension within the Badger GUI."""

import logging
import time
from dataclasses import dataclass
from typing import Optional

from PyQt5.QtWidgets import QWidget
from xopt.generators.bayesian.bax_generator import BaxGenerator
from xopt.generators.bayesian.bayesian_generator import BayesianGenerator

from badger.gui.components.analysis_widget import AnalysisWidget
from badger.gui.components.bax_visualizer.ui import UI
from badger.gui.components.extension_utilities import HandledException, requires_update
from badger.routine import Routine
from badger.utils import create_archive_run_filename

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Parameters:
    n_grid: int = 50
    n_samples: int = 100
    fig_size: tuple[int, int] = (5, 5)


DEFAULT_PARAMETERS = Parameters(n_grid=50, n_samples=100, fig_size=(5, 5))


class BaxWidget(AnalysisWidget):
    parameters = DEFAULT_PARAMETERS
    generator: BaxGenerator

    def __init__(self, routine: Routine, parent: Optional[QWidget] = None):
        logger.debug("Initializing BaxWidget")
        super().__init__(routine=routine, parent=parent)

        self.ui = UI(routine=self.routine, parameters=self.parameters, parent=self)

        self.setWindowTitle("BAX Visualizer")
        self.setMinimumSize(800, 600)

    def initialize_widget(self) -> None:
        pass

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
        self.initialized = False
        self.routine_identifier = ""
        self.df_length = float("inf")

    def update_plots(self, requires_rebuild: bool, interval: int) -> None:
        if not requires_update(self.last_updated, interval, requires_rebuild):
            return

        self.ui.plotting_area.update_tab_widget()

        self.last_updated = time.time()

    def setup_connections(self) -> None:
        pass

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
