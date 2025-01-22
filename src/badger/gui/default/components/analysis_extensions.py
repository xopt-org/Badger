from abc import abstractmethod
from typing import Optional, cast

import pyqtgraph as pg
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QMessageBox
from PyQt5.QtGui import QCloseEvent
from badger.gui.default.components.bo_visualizer.bo_plotter import BOPlotWidget
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
    def __init__(self, parent: Optional[AnalysisExtension] = None):
        super().__init__(parent=parent)

        self.setWindowTitle("Pareto Front Viewer")

        self.plot_widget = pg.PlotWidget()

        self.scatter_plot = self.plot_widget.plot(pen=None, symbol="o", symbolSize=10)

        layout = QVBoxLayout()
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

    def update_window(self, routine: Routine):
        if len(routine.vocs.objective_names) != 2:
            raise ValueError(
                "cannot use pareto front viewer unless there are 2 " "objectives"
            )

        x_name = routine.vocs.objective_names[0]
        y_name = routine.vocs.objective_names[1]

        if routine.data is not None:
            x = routine.data[x_name]
            y = routine.data[y_name]

            # Update the scatter plot
            self.scatter_plot.setData(x=x, y=y)

        # set labels
        self.plot_widget.setLabel("left", y_name)
        self.plot_widget.setLabel("bottom", x_name)


class BOVisualizer(AnalysisExtension):
    df_length = float("inf")
    initialized = False

    def __init__(self, parent: Optional[AnalysisExtension] = None):
        logger.debug("Initializing BO Visualizer Extension")

        super().__init__(parent=parent)
        self.setWindowTitle("BO Visualizer")

        # Initialize BOPlotWidget without a routine
        self.bo_plot_widget = BOPlotWidget()

        logger.debug("Initialized BOPlotWidget")

        bo_layout = QVBoxLayout()
        bo_layout.addWidget(self.bo_plot_widget)
        self.setLayout(bo_layout)

        logger.debug("Set layout for BOVisualizer")

    def requires_reinitialization(self, routine: Routine):
        # Check if the extension needs to be reinitialized

        if not self.initialized:
            logger.debug("Reset - Extension never initialized")
            self.initialized = True
            return True

        if routine.data is None:
            logger.debug("Reset - No data available")
            return True

        previous_len = self.df_length
        self.df_length = len(routine.data)
        new_length = self.df_length

        if previous_len > new_length:
            logger.debug("Reset - Data length is the same or smaller")
            self.df_length = float("inf")
            return True

        return False

    def update_window(self, routine: Routine):
        # Updating the BO Visualizer window
        logger.debug("Updating BO Visualizer window")

        # Update the routine with new generator model if applicable
        self.update_routine(routine)

        if self.requires_reinitialization(self.routine):
            self.bo_plot_widget.initialize_widget(self.routine)

        # Update the plots with the new generator model
        self.bo_plot_widget.update_plot(100)

    def update_routine(self, routine: Routine):
        logger.debug("Updating routine in BO Visualizer")

        generator = cast(BayesianGenerator, routine.generator)

        if generator.data is None:
            logger.warning("No data available in generator")

            if routine.data is None:
                logger.warning("No data available in routine or generator")
            else:
                # Handle the edge case where the extension has been opened after an optimization has already finished.
                logger.debug("Setting generator data from routine")

                # Use the data from the routine to train the model
                generator.data = routine.data

                try:
                    generator.train_model()
                except Exception as e:
                    logger.error(f"Failed to train model: {e}")
                    QMessageBox.warning(
                        self,
                        "Failed to train model",
                        f"Failed to train model: {e}",
                    )

        else:
            self.df_length = len(generator.data)

        routine.generator = generator
        self.routine = routine
