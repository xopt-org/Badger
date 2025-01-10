from abc import abstractmethod
from typing import Optional

import pyqtgraph as pg
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QVBoxLayout
from PyQt5.QtGui import QCloseEvent
from badger.gui.default.components.bo_visualizer.bo_plotter import BOPlotWidget
from badger.routine import Routine

import logging

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
    # requires_model_rebuild = True

    def __init__(self, parent: Optional[AnalysisExtension] = None):
        logger.debug("Initializing BOVisualizer")
        super().__init__(parent=parent)
        self.setWindowTitle("BO Visualizer")
        self.bo_plot_widget: Optional[BOPlotWidget] = None

    def requires_reinitialization(self, routine: Routine):
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
            # self.requires_model_rebuild = True
            return True

        return False

    def update_window(self, routine: Routine):
        # Update the BOPlotWidget with the new routine
        logger.debug("Updating BOVisualizer window with new routine")

        # Initialize the BOPlotWidget if it is not already initialized
        if self.bo_plot_widget is None:
            # Initialize BOPlotWidget without an xopt_obj
            self.bo_plot_widget = BOPlotWidget()

            logger.debug("Initialized BOPlotWidget")

            bo_layout = QVBoxLayout()
            bo_layout.addWidget(self.bo_plot_widget)
            self.setLayout(bo_layout)
            logger.debug("Set layout for BOVisualizer")

            if routine.data is not None:
                self.df_length = len(routine.data)

        # If there is no data available, then initialize the plot
        # This needs to happen when starting a new optimization run

        if self.requires_reinitialization(routine):
            self.bo_plot_widget.initialize_widget(routine)

        # logger.debug(
        #     f"Does the model need to be rebuilt? - {self.requires_model_rebuild}"
        # )

        # Update the plot with every call to update_window
        # This is necessary when continuing an optimiza tion run
        self.bo_plot_widget.update_plot(100)
