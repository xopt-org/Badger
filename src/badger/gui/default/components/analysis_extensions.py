from abc import abstractmethod
from typing import Optional, cast

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QMessageBox
from PyQt5.QtGui import QCloseEvent
from badger.gui.default.components.bo_visualizer.bo_plotter import BOPlotWidget
from badger.gui.default.components.pf_viewer.pf_widget import ParetoFrontWidget
from badger.routine import Routine

import logging

from xopt.generators.bayesian.bayesian_generator import BayesianGenerator

logger = logging.getLogger(__name__)


class AnalysisExtension(QDialog):
    window_closed = pyqtSignal(object)

    def __init__(self, parent: Optional[QDialog] = None):
        super().__init__(parent=parent)

    @abstractmethod
    def update_window(self, routine: Routine):
        pass

    def closeEvent(self, a0: Optional[QCloseEvent]) -> None:
        self.window_closed.emit(self)
        super().closeEvent(a0)


class ParetoFrontViewer(AnalysisExtension):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Pareto Front Viewer")

        self.pw_widget = ParetoFrontWidget()

        layout = QVBoxLayout()
        layout.addWidget(self.pw_widget)
        self.setLayout(layout)

    def update_window(self, routine: Routine):
        try:
            self.pw_widget.update_plot(routine)
        except:
            self.close()


class BOVisualizer(AnalysisExtension):
    df_length = float("inf")
    initialized = False
    correct_generator = False
    routine_identifier = ""
    plot_update_rate = 250

    def __init__(self):
        logger.debug("Initializing BO Visualizer Extension")

        super().__init__()
        self.setWindowTitle("BO Visualizer")

        # Initialize BOPlotWidget without a routine
        self.bo_plot_widget = BOPlotWidget()

        logger.debug("Initialized BOPlotWidget")

        bo_layout = QVBoxLayout()
        bo_layout.addWidget(self.bo_plot_widget)
        self.setLayout(bo_layout)

        logger.debug("Set layout for BOVisualizer")

    def requires_reinitialization(self):
        # Check if the extension needs to be reinitialized
        logger.debug("Checking if BO Visualizer needs to be reinitialized")

        if not self.initialized:
            logger.debug("Reset - Extension never initialized")
            self.initialized = True
            return True

        if self.routine_identifier != self.routine.name:
            logger.debug("Reset - Routine name has changed")
            self.identifier = self.routine.name
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

    def update_window(self, routine: Routine):
        # Updating the BO Visualizer window
        logger.debug("Updating BO Visualizer window")

        try:
            # Update the routine with new generator model if applicable
            self.update_routine(routine)
        except:
            self.close()

        if not self.correct_generator:
            logger.debug("Incorrect generator type")
            return

        if self.requires_reinitialization():
            self.bo_plot_widget.initialize_widget(self.routine, self.update_window)

        # Update the plots with the new generator model
        self.bo_plot_widget.update_plot(self.plot_update_rate)

    def update_routine(self, routine: Routine):
        logger.debug("Updating routine in BO Visualizer")

        self.routine = routine

        # Check if the generator is a BayesianGenerator
        if not issubclass(self.routine.generator.__class__, BayesianGenerator):
            self.correct_generator = False
            QMessageBox.critical(
                self,
                "Invalid Generator",
                f"Invalid generator type: {type(self.routine.generator)}, BO Visualizer only supports BayesianGenerator",
            )
            raise TypeError(
                f"Invalid generator type: {type(self.routine.generator)}, BO Visualizer only supports BayesianGenerator"
            )

        self.correct_generator = True

        generator = cast(BayesianGenerator, self.routine.generator)

        # Handle the edge case where the extension has been opened after an optimization has already finished.
        if generator.model is None:
            logger.warning("Model not found in generator")
            if generator.data is None:
                if self.routine.data is None:
                    logger.error("No data available in routine or generator")
                    QMessageBox.critical(
                        self,
                        "No data available",
                        "No data available in routine or generator",
                    )
                    return

                # Use the data from the routine to train the model
                logger.debug("Setting generator data from routine")
                generator.data = self.routine.data

            try:
                generator.train_model(generator.data)
            except Exception as e:
                logger.error(f"Failed to train model: {e}")
                QMessageBox.warning(
                    self,
                    "Failed to train model",
                    f"Failed to train model: {e}",
                )
        else:
            logger.debug("Model already exists in generator")

        if generator.data is None:
            logger.error("No data available in generator")
            QMessageBox.critical(
                self,
                "No data available",
                "No data available in generator",
            )
            return

        self.df_length = len(generator.data)
        self.routine.generator = generator
