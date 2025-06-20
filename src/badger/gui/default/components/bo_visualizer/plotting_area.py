from typing import Optional, cast
from badger.gui.default.components.extension_utilities import (
    BlockSignalsContext,
    MatplotlibFigureContext,
    clear_layout,
    requires_update,
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QMessageBox
from xopt.generators.bayesian.visualize import (
    visualize_generator_model,
)
from xopt.generators.bayesian.bayesian_generator import BayesianGenerator

import time


import logging

logger = logging.getLogger(__name__)

# plt.switch_backend("Qt5Agg")


class PlottingArea(QWidget):
    last_updated: Optional[float] = None

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Create a layout for the plot area without pre-filling it with a plot
        _layout = QVBoxLayout()
        self.setLayout(_layout)

    def update_plot(
        self,
        generator: BayesianGenerator,
        variable_names: list[str],
        reference_point: dict[str, float],
        show_acquisition: bool,
        show_samples: bool,
        show_prior_mean: bool,
        show_feasibility: bool,
        n_grid: int,
        requires_rebuild: bool = False,
        interval: int = 1000,  # Interval in milliseconds
    ):
        logger.debug("Updating plot in PlottingArea")

        # Check if the plot was updated recently
        if not requires_update(self.last_updated, interval, requires_rebuild):
            logger.debug("Plot not updated due to interval restriction")
            return

        if generator.model is None:
            logger.debug("Model not found")
            return

        try:
            # Generate the new plot using visualize_generator_model
            fig, ax = cast(
                tuple[Figure, Axes],
                visualize_generator_model(
                    generator,
                    variable_names=variable_names,
                    reference_point=reference_point,
                    show_acquisition=show_acquisition,
                    show_samples=show_samples,
                    show_prior_mean=show_prior_mean,
                    show_feasibility=show_feasibility,
                    n_grid=n_grid,
                ),
            )

            layout = self.layout()

            if layout is not None:
                with BlockSignalsContext(layout):
                    # Clear the existing layout (remove previous plot if any)
                    clear_layout(layout)

                    with MatplotlibFigureContext(fig, ax) as (fig, ax):
                        # Set the layout engine to tight
                        # fig.show()

                        # Create a new figure and canvas
                        canvas = FigureCanvas(fig)

                        # Add the new canvas to the layout
                        layout.addWidget(canvas)

                    # plt.close(fig)  # Close the figure to free memory
            else:
                raise Exception("Layout never updated")
        except Exception as e:
            logger.error(f"Error updating plot: {e}")
            QMessageBox.critical(
                self,
                "Plot Update Error",
                f"An error occurred while updating the plot: {e}",
            )
            raise Exception(f"An error occurred while updating the plot: {e}")
        # Update the last updated time
        self.last_updated = time.time()
