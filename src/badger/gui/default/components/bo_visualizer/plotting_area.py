from collections.abc import Callable
from typing import Optional, cast
from badger.gui.default.components.bo_visualizer.types import ConfigurableOptions
from badger.gui.default.components.extension_utilities import (
    BlockSignalsContext,
    HandledException,
    MatplotlibFigureContext,
    clear_layout,
    requires_update,
)
from badger.routine import Routine
from matplotlib.backends.backend_qtagg import (
    FigureCanvasQTAgg as FigureCanvas,
)
from matplotlib.backends.backend_qt import (
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from PyQt5.QtWidgets import QVBoxLayout, QWidget
from xopt.generators.bayesian.visualize import (
    visualize_generator_model,
)
from xopt.generators.bayesian.bayesian_generator import BayesianGenerator

import time
from badger.gui.default.components.plot_event_handlers import (
    MatplotlibInteractionHandler,
)


import logging

logger = logging.getLogger(__name__)


class PlottingArea(QWidget):
    last_updated: Optional[float] = None

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)

        # Create a layout for the plot area without pre-filling it with a plot
        _layout = QVBoxLayout()
        self.setLayout(_layout)

    def update_plot(
        self,
        routine: Routine,
        generator: BayesianGenerator,
        parameters: ConfigurableOptions,
        update_extension: Callable[[Routine, bool], None],
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
                        # Create a new figure and canvas
                        canvas = FigureCanvas(fig)
                        toolbar = NavigationToolbar(canvas, self)

                        handler = MatplotlibInteractionHandler(
                            canvas, parameters, routine, update_extension
                        )
                        handler.connect_events()

                        # Add the new canvas to the layout
                        layout.addWidget(canvas)
                        layout.addWidget(toolbar)
            else:
                raise HandledException(ValueError, "Layout is None and is not updated")
        except HandledException as he:
            raise he
        except Exception as e:
            logger.error(f"Error updating plot: {e}")
            raise e
        # Update the last updated time
        self.last_updated = time.time()
