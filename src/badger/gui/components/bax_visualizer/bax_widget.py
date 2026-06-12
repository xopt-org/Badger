from typing import Optional

from PyQt5.QtWidgets import QDialog
from xopt.generators.bayesian.bayesian_generator import BayesianGenerator

from badger.gui.components.analysis_widget import AnalysisWidget
from badger.gui.components.extension_utilities import HandledException
from badger.routine import Routine


class BaxWidget(AnalysisWidget):  # type: ignore[misc]
    def __init__(self, routine: Routine, parent: Optional[QDialog] = None):
        super().__init__(routine=routine, parent=parent)

    def initialize_widget(self) -> None:
        pass

    def requires_reinitialization(self) -> bool:
        return False

    def update_plots(self, requires_rebuild: bool, interval: int) -> None:
        pass

    def setup_connections(self) -> None:
        pass

    def isValidRoutine(self, routine: Routine) -> None:
        if not isinstance(routine.generator, BayesianGenerator):
            raise HandledException(
                ValueError, "Bax Visualizer can only be used with a BayesianGenerator."
            )
