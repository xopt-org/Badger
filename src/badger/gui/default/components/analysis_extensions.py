from abc import abstractmethod
from typing import Optional

import pyqtgraph as pg
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QVBoxLayout
from badger.gui.default.components.bo_visualizer.bo_plotter import BOPlotWidget
from badger.core import Routine

import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class AnalysisExtension(QDialog):
    window_closed = pyqtSignal(object)

    def __init__(self, parent: Optional[QDialog] = None):
        super().__init__(parent=parent)

    @abstractmethod
    def update_window(self, routine: Routine):
        pass

    def closeEvent(self, event) -> None:
        self.window_closed.emit(self)
        super().closeEvent(event)


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
    df_length = 0

    def __init__(self, parent: Optional[AnalysisExtension] = None):
        logger.debug("Initializing BOVisualizer")
        super().__init__(parent=parent)
        self.setWindowTitle("BO Visualizer")
        self.bo_plot_widget: Optional[BOPlotWidget] = None

    def requires_update(self, routine: Routine):
        if routine.data is None:
            logger.debug("Reset - No data available")
            return True

        if self.bo_plot_widget.model_logic.xopt_obj is None:
            logger.debug("Reset - xopt_obj is None")
            return True

        if len(routine.data) <= self.df_length:
            logger.debug("Reset - Data length is the same or smaller")
            self.df_length = len(routine.data)
            return True

        return False

    def update_window(self, routine: Routine):
        # Update the BOPlotWidget with the new routine
        logger.debug("Updating BOVisualizer window with new routine")
        self.df_length = len(routine.data)
        # logger.debug(f"Routine {routine.data}")

        # Initialize the BOPlotWidget if it is not already initialized
        if self.bo_plot_widget is None:
            # Initialize BOPlotWidget without an xopt_obj
            self.bo_plot_widget = BOPlotWidget()

            logger.debug("Initialized BOPlotWidget")

            bo_layout = QVBoxLayout()
            bo_layout.addWidget(self.bo_plot_widget)
            self.setLayout(bo_layout)
            logger.debug("Set layout for BOVisualizer")

        else:
            logger.debug("BOPlotWidget already initialized")

        # If there is no data available, then initialize the plot
        # This needs to happen when starting a new optimization run

        if self.requires_update(routine):
            self.bo_plot_widget.initialize_plot(routine)
            logger.debug(f"Data: {self.bo_plot_widget.model_logic.xopt_obj.data}")
        else:
            logger.debug("BOPlotWidget already has data")

        # Update the plot with every call to update_window
        # This is necessary when continuing an optimization run
        self.bo_plot_widget.update_plot(100)
