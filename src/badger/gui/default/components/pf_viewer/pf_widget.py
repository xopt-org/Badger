from typing import Optional
from PyQt5.QtWidgets import QWidget
from PyQt5.QtWidgets import QVBoxLayout
import pyqtgraph as pg
from badger.routine import Routine

from xopt.generators.bayesian.mobo import MOBOGenerator

import logging

logger = logging.getLogger(__name__)


class ParetoFrontWidget(QWidget):
    routine = None

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent=parent)
        self.plot_widget = pg.PlotWidget()
        self.scatter_plot = self.plot_widget.plot(pen=None, symbol="o", symbolSize=10)
        layout = QVBoxLayout()
        layout.addWidget(self.plot_widget)
        self.setLayout(layout)

    def isValidRoutine(self, routine: Routine):
        if routine.vocs.objective_names is None:
            logging.error("No objective names")
            return False
        if len(routine.vocs.objective_names) != 2:
            logging.error("Invalid number of objectives")
            return False
        return

    def update_plot(self, routine: Routine):
        self.routine = routine

        if not self.isValidRoutine(self.routine):
            logging.error("Invalid routine")
            return

        if not isinstance(self.routine.generator, MOBOGenerator):
            logging.error("Invalid generator")
            return

        pareto_front = self.routine.generator.get_pareto_front()

        if pareto_front == (None, None):
            logging.error("No pareto front")
            return

        # aquisition_fn = self.routine.generator.get_acquisition(pareto_front)

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
