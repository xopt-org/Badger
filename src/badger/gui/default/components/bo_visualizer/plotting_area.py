from typing import Optional, cast
from matplotlib import pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from PyQt5.QtWidgets import QVBoxLayout, QWidget, QMessageBox
from xopt.generators.bayesian.visualize import visualize_generator_model
from xopt.generators.bayesian.bayesian_generator import BayesianGenerator

from badger.routine import Routine
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
        xopt_obj: Optional[Routine],
        variable_names: list[str],
        reference_point: dict[str, float],
        show_acquisition: bool,
        show_samples: bool,
        show_prior_mean: bool,
        show_feasibility: bool,
        n_grid: int,
        requires_rebuild: bool,
        interval: Optional[float] = 1000.0,  # Interval in milliseconds
    ):
        logger.debug("Updating plot in PlottingArea")

        # Check if the plot was updated recently
        if self.last_updated is not None and interval is not None:
            logger.debug(f"Time since last update: {time.time() - self.last_updated}")

            time_diff = time.time() - self.last_updated

            # If the plot was updated less than 1 second ago, skip this update
            if time_diff < interval / 1000:
                logger.debug("Skipping update")
                return

        if not xopt_obj:
            print("Xopt object is not available. Cannot update plot.")
            return

        xopt_data = xopt_obj.data

        if xopt_data is None:
            logger.error("Xopt Data from Routine is None")
            return

        generator = cast(BayesianGenerator, xopt_obj.generator)

        # Ensure use_cuda is a boolean
        generator.use_cuda = False  # or True, depending on your setup

        # Set generator data
        generator.data = xopt_data
        logger.debug(f"Generator data: {generator.data}")

        if requires_rebuild:
            generator.model = None

        # Check if the model exists
        if not hasattr(generator, "model") or generator.model is None:
            # Attempt to train the model
            print("Model not found. Training the model...")
            try:
                generator.train_model()

            except Exception as e:
                print(f"Failed to train model: {e}")
                logger.error(f"Failed to train model: {e}")
                QMessageBox.warning(
                    self, "Model Training Error", f"Failed to train model: {e}"
                )
                return

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

        logger.debug(f"Layout exists: {layout}")

        if layout is not None:
            # Clear the existing layout (remove previous plot if any)
            for i in reversed(range(layout.count())):
                layout_item = layout.itemAt(i)
                if layout_item is not None:
                    widget_to_remove = layout_item.widget()
                    if widget_to_remove is not None:
                        widget_to_remove.setParent(None)

            # Create a new figure and canvas
            figure = Figure()
            canvas = FigureCanvas(figure)
            # Set the new figure to the canvas and draw it
            canvas.figure = fig
            canvas.draw()

            # Add the new canvas to the layout
            layout.addWidget(canvas)
        else:
            raise Exception("Layout never updated")

        # Ensure the layout is updated
        self.updateGeometry()

        # Close the old figure to prevent memory leaks
        plt.close(fig)

        # Update the last updated time
        self.last_updated = time.time()
