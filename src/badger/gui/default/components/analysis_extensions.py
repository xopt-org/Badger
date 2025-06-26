from abc import abstractmethod
from typing import Optional
import logging

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QVBoxLayout
from PyQt5.QtGui import QCloseEvent
from badger.gui.default.components.bo_visualizer.bo_plotter import BOPlotWidget
from badger.gui.default.components.pf_viewer.pf_widget import ParetoFrontWidget
from badger.routine import Routine

from xopt.generators.bayesian.bayesian_generator import BayesianGenerator
from xopt.generators.bayesian.mobo import MOBOGenerator

logger = logging.getLogger(__name__)


class AnalysisExtension(QDialog):
    window_closed = pyqtSignal(object)
    widget = None

    def __init__(self, parent: Optional[QDialog] = None):
        super().__init__(parent=parent)

    @abstractmethod
    def update_window(self, routine: Routine) -> None:
        pass

    @abstractmethod
    def update_extension(self, routine: Routine) -> None:
        """
        Update the extension with the new routine.
        This method should be implemented to handle the update logic for the extension.
        """
        pass

    def closeEvent(self, a0: Optional[QCloseEvent]) -> None:
        self.window_closed.emit(self)
        super().closeEvent(a0)


class ParetoFrontViewer(AnalysisExtension):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Pareto Front Viewer")

        self.widget = ParetoFrontWidget()
        self.widget.update_extension = self.update_extension

        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        self.setLayout(layout)

    def update_extension(self, routine: Routine, requires_rebuild: bool = False):
        self.widget.isValidRoutine(routine)

        self.widget.update_routine(routine, MOBOGenerator)

        if self.widget.requires_reinitialization():
            self.widget.initialize_widget()

        self.widget.update_plots(requires_rebuild, interval=self.widget.update_interval)

    def update_window(self, routine: Routine):
        try:
            self.update_extension(routine)
        except Exception as e:
            raise e


class BOVisualizer(AnalysisExtension):
    def __init__(self):
        logger.debug("Initializing BO Visualizer Extension")

        super().__init__()
        self.setWindowTitle("BO Visualizer")

        # Initialize BOPlotWidget without a routine
        self.widget = BOPlotWidget()
        self.widget.update_extension = self.update_extension

        logger.debug("Initialized BOPlotWidget")

        bo_layout = QVBoxLayout()
        bo_layout.addWidget(self.widget)
        self.setLayout(bo_layout)

        logger.debug("Set layout for BOVisualizer")

    def update_extension(self, routine: Routine, requires_rebuild: bool = False):
        # Update the routine with new generator model if applicable
        self.widget.update_routine(routine, BayesianGenerator)

        if self.widget.requires_reinitialization():
            self.widget.initialize_widget()

        # Update the plots with the new generator model
        self.widget.update_plot(requires_rebuild, interval=self.widget.update_interval)

    def update_window(self, routine: Routine):
        # Updating the BO Visualizer window
        logger.debug("Updating BO Visualizer window")

        try:
            self.update_extension(routine)
        except Exception as e:
            raise e
