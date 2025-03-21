import time
from typing import Optional, cast
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QLayout
from badger.routine import Routine

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from xopt.generators.bayesian.mobo import MOBOGenerator
from xopt.generators.bayesian.bayesian_generator import visualize_generator_model

import logging

logger = logging.getLogger(__name__)


class ParetoFrontWidget(QWidget):
    routine: Routine
    df_length: int
    correct_generator: bool
    last_updated: Optional[float] = None

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent=parent)
        self.plot_widget = QVBoxLayout()
        layout = QVBoxLayout()
        layout.addLayout(self.plot_widget)
        self.setLayout(layout)

    def isValidRoutine(self, routine: Routine):
        if routine.vocs.objective_names is None:
            logging.error("No objective names")
            return False
        if len(routine.vocs.objective_names) < 2:
            logging.error("Invalid number of objectives")
            return False

        return True

    def create_pareto_plot(
        self, generator: MOBOGenerator, requires_rebuild=False, interval=1000
    ):
        if generator.model is None:
            logging.error("Model not found in generator")
            return

        # Check if the plot was updated recently
        if (
            self.last_updated is not None
            and interval is not None
            and not requires_rebuild
        ):
            logger.debug(f"Time since last update: {time.time() - self.last_updated}")

            time_diff = time.time() - self.last_updated

            # If the plot was updated less than 1 second ago, skip this update
            if time_diff < interval / 1000:
                logger.debug("Skipping update")
                return

        # pareto_front = generator.get_pareto_front()

        # if pareto_front[0] is None or pareto_front[1] is None:
        #     logging.error("No pareto front")
        #     return

        # fig = Figure()
        # ax = fig.add_subplot()
        # ax.plot(pareto_front, "ro")

        fig, ax = visualize_generator_model(
            generator=generator,
            variable_names=generator.vocs.variable_names,
            reference_point=generator.reference_point,
            show_acquisition=True,
            show_samples=True,
            show_prior_mean=True,
            show_feasibility=True,
            n_grid=100,
        )

        self.clearLayout(self.plot_widget)

        canvas = FigureCanvas(fig)

        self.plot_widget.addWidget(canvas)

        plt.close(fig)

        # Update the last updated time
        self.last_updated = time.time()

    def create_hypervolume_plot(self, generator: MOBOGenerator):
        hypervolume = generator.calculate_hypervolume()

        logging.debug(f"Pareto front hypervolume: {hypervolume}")

        return hypervolume

    def clearLayout(self, layout: QLayout):
        while layout.count():
            child = layout.takeAt(0)
            if child is None:
                break

            widget = child.widget()
            if widget is None:
                break

            widget.deleteLater()

    def update_plot(self, routine: Routine):
        self.update_routine(routine)

        if not self.isValidRoutine(self.routine):
            logging.error("Invalid routine")
            return

        if not isinstance(self.routine.generator, MOBOGenerator):
            logging.error("Invalid generator")
            return False

        self.create_pareto_plot(self.routine.generator)

        hypervolume = self.create_hypervolume_plot(self.routine.generator)
        logger.debug(f"Pareto front hypervolume: {hypervolume}")

    def update_routine(self, routine: Routine):
        logger.debug("Updating routine in BO Visualizer")

        self.routine = routine

        # Check if the generator is a BayesianGenerator
        if not issubclass(self.routine.generator.__class__, MOBOGenerator):
            self.correct_generator = False
            QMessageBox.critical(
                self,
                "Invalid Generator",
                f"Invalid generator type: {type(self.routine.generator)}, BO Visualizer only supports BayesianGenerator",
            )
            return

        self.correct_generator = True

        generator = cast(MOBOGenerator, self.routine.generator)

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
