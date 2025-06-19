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

        layout = QVBoxLayout()
        layout.addWidget(self.widget)
        self.setLayout(layout)

    def update_extension(self, routine: Routine):
        if not self.widget.isValidRoutine(routine):
            logging.error("Invalid routine")
            return

        self.widget.update_routine(routine, MOBOGenerator)

        if self.widget.requires_reinitialization():
            self.widget.initialize_ui()

        self.widget.update_plots(interval=self.widget.update_interval)

    def update_window(self, routine: Routine):
        try:
            self.update_extension(routine)
        except:
            self.close()


class BOVisualizer(AnalysisExtension):
    def __init__(self):
        logger.debug("Initializing BO Visualizer Extension")

        super().__init__()
        self.setWindowTitle("BO Visualizer")

        # Initialize BOPlotWidget without a routine
        self.widget = BOPlotWidget()

        logger.debug("Initialized BOPlotWidget")

        bo_layout = QVBoxLayout()
        bo_layout.addWidget(self.widget)
        self.setLayout(bo_layout)

        logger.debug("Set layout for BOVisualizer")

    def update_extension(self, routine: Routine):
        # Update the routine with new generator model if applicable
        self.widget.update_routine(routine, BayesianGenerator)

        if self.widget.requires_reinitialization():
            self.widget.initialize_widget(self.widget.routine, self.update_window)

        # Update the plots with the new generator model
        self.widget.update_plot(interval=self.widget.update_interval)

    def update_window(self, routine: Routine):
        # Updating the BO Visualizer window
        logger.debug("Updating BO Visualizer window")

        try:
            self.update_extension(routine)
        except:
            self.close()

    # def update_routine(self, routine: Routine):
    #     logger.debug("Updating routine in BO Visualizer")

    #     self.routine = routine

    #     # Check if the generator is a BayesianGenerator
    #     if not issubclass(self.routine.generator.__class__, BayesianGenerator):
    #         self.correct_generator = False
    #         QMessageBox.critical(
    #             self,
    #             "Invalid Generator",
    #             f"Invalid generator type: {type(self.routine.generator)}, BO Visualizer only supports BayesianGenerator",
    #         )
    #         raise TypeError(
    #             f"Invalid generator type: {type(self.routine.generator)}, BO Visualizer only supports BayesianGenerator"
    #         )

    #     self.correct_generator = True

    #     generator = cast(BayesianGenerator, self.routine.generator)

    #     # Handle the edge case where the extension has been opened after an optimization has already finished.
    #     if generator.model is None:
    #         logger.warning("Model not found in generator")
    #         if generator.data is None:
    #             if self.routine.data is None:
    #                 logger.error("No data available in routine or generator")
    #                 QMessageBox.critical(
    #                     self,
    #                     "No data available",
    #                     "No data available in routine or generator",
    #                 )
    #                 return

    #             # Use the data from the routine to train the model
    #             logger.debug("Setting generator data from routine")
    #             generator.data = self.routine.data

    #         try:
    #             generator.train_model(generator.data)
    #         except Exception as e:
    #             logger.error(f"Failed to train model: {e}")
    #             QMessageBox.warning(
    #                 self,
    #                 "Failed to train model",
    #                 f"Failed to train model: {e}",
    #             )
    #     else:
    #         logger.debug("Model already exists in generator")

    #     if generator.data is None:
    #         logger.error("No data available in generator")
    #         QMessageBox.critical(
    #             self,
    #             "No data available",
    #             "No data available in generator",
    #         )
    #         return

    #     self.df_length = len(generator.data)
    #     self.routine.generator = generator
