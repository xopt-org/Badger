from typing import Optional, cast
from badger.gui.default.components.extension_utilities import (
    clear_layout,
    requires_update,
)
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from PyQt5.QtWidgets import QVBoxLayout, QWidget
from xopt.generators.bayesian.visualize import (
    visualize_generator_model,
)
from xopt.generators.bayesian.bayesian_generator import BayesianGenerator

import time


import logging

logger = logging.getLogger(__name__)

plt.switch_backend("Qt5Agg")


class PlottingArea(QWidget):
    last_updated: Optional[float] = None

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Create a layout for the plot area without pre-filling it with a plot
        _layout = QVBoxLayout()
        self.setLayout(_layout)
        self.last_updated = time.time()

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

        debug_object = {
            "variable_names": variable_names,
            "reference_point": reference_point,
            "show_acquisition": show_acquisition,
            "show_samples": show_samples,
            "show_prior_mean": show_prior_mean,
            "show_feasibility": show_feasibility,
            "n_grid": n_grid,
            "requires_rebuild": requires_rebuild,
            "interval": interval,
        }

        # Check if the plot was updated recently
        if not requires_update(self.last_updated, interval, requires_rebuild):
            logger.debug("Plot not updated due to interval restriction")
            return

        if generator.model is None:
            logger.debug("Model not found")
            return

        logger.debug(f"Arguments: {debug_object}")

        # Generate the new plot using visualize_generator_model
        fig, _ = cast(
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

        # Adjust padding inside the figure
        fig.tight_layout(pad=1)  # Adds padding between plot elements

        layout = self.layout()

        if layout is not None:
            # Clear the existing layout (remove previous plot if any)
            clear_layout(layout)

            # Create a new figure and canvas
            canvas = FigureCanvas(fig)

            # Add the new canvas to the layout
            layout.addWidget(canvas)

            # Close the old figure to prevent memory leaks
            plt.close(fig)

        else:
            raise Exception("Layout never updated")

        # Ensure the layout is updated
        self.updateGeometry()
        self.adjustSize()

        # Update the last updated time
        self.last_updated = time.time()
