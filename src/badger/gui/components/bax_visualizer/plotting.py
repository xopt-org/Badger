"""Matplotlib-based plotting widget for visualizing BAX virtual measurements."""

import logging
import os
import sys
from typing import TYPE_CHECKING, Optional

from matplotlib.axes import Axes
from matplotlib.backends.backend_qt import NavigationToolbar2QT
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5.QtWidgets import QTabWidget, QVBoxLayout, QWidget
from xopt.generators.bayesian.bax_generator import BaxGenerator

from badger.gui.components.extension_utilities import (
    MatplotlibFigureContext,
    clear_tabs,
)
from badger.utils import BlockSignalsContext

# Temporary: the vendored ``bax_algorithms`` package uses absolute imports
# rooted at the top-level name ``bax_algorithms`` (e.g.
# ``from bax_algorithms.utils import ...``). Add the directory that contains the
# package to ``sys.path`` so it is importable as a top-level package until it is
# properly published as part of xopt.
_BAX_ALGORITHMS_DIR = os.path.join(os.path.dirname(__file__), "bax_algorithms")
if _BAX_ALGORITHMS_DIR not in sys.path:
    sys.path.insert(0, _BAX_ALGORITHMS_DIR)

from bax_algorithms.visualize import (  # noqa: E402
    plot_bax_input_convergence,
    plot_bax_objective_convergence,
    visualize_virtual_measurement_result,
)

if TYPE_CHECKING:
    from badger.gui.components.bax_visualizer.bax_widget import Parameters


logger = logging.getLogger(__name__)


class PlottingWidget(QWidget):
    def __init__(
        self,
        generator: BaxGenerator,
        parameters: "Parameters",
        parent: Optional[QWidget] = None,
    ):
        logger.debug("Initializing PlottingWidget")
        super().__init__(parent=parent)

        self.generator = generator
        self.parameters = parameters
        self._initialize_plotting_area()

    def _initialize_plotting_area(self) -> None:
        main_layout = QVBoxLayout()
        self.plot_tab_widget = QTabWidget()

        main_layout.addWidget(self.plot_tab_widget)

        self.setLayout(main_layout)

        self.update_tab_widget()

    def create_first_plot(self) -> tuple[Figure, Axes]:
        logger.debug("Creating first plot")
        fig, ax = visualize_virtual_measurement_result(
            self.generator,
            variable_names=["x0", "x1"],
            idx=0,
            reference_point=None,  # type: ignore[arg-type]
            n_grid=self.parameters.n_grid,
            n_samples=self.parameters.n_samples,
            show_observations=True,
            result_keys=["objective"],
        )
        return fig, ax

    def create_second_plot(self) -> tuple[Figure, Axes]:
        logger.debug("Creating second plot")
        fig, ax = plot_bax_objective_convergence(
            self.generator,
        )
        return fig, ax

    def create_third_plot(self) -> tuple[Figure, Axes]:
        logger.debug("Creating third plot")
        fig, ax = plot_bax_input_convergence(
            self.generator,
        )
        return fig, ax

    def update_first_tab(self) -> None:

        with MatplotlibFigureContext(fig_size=self.parameters.fig_size) as (fig, ax):
            try:
                fig, ax = self.create_first_plot()
                canvas = FigureCanvasQTAgg(fig)  # type: ignore[no-untyped-call]
                toolbar = NavigationToolbar2QT(canvas, self)  # type: ignore[no-untyped-call]

                # handler = MatplotlibInteractionHandler(canvas, )

                widget = QWidget()
                layout = QVBoxLayout()
                layout.addWidget(canvas)
                layout.addWidget(toolbar)
                widget.setLayout(layout)
                self.plot_tab_widget.addTab(widget, "FirstPlot")

            except Exception as e:
                logger.error(f"Error creating plot: {e}")
                blank_canvas = FigureCanvasQTAgg(fig)  # type: ignore[no-untyped-call]
                self.plot_tab_widget.addTab(blank_canvas, "Error")

    def update_second_tab(self) -> None:

        widget = QWidget()
        layout = QVBoxLayout()

        with MatplotlibFigureContext(fig_size=self.parameters.fig_size) as (fig, ax):
            try:
                fig, ax = self.create_second_plot()
                canvas = FigureCanvasQTAgg(fig)  # type: ignore[no-untyped-call]
                toolbar = NavigationToolbar2QT(canvas, self)  # type: ignore[no-untyped-call]

                # handler = MatplotlibInteractionHandler(canvas, )

                layout.addWidget(canvas)
                layout.addWidget(toolbar)

            except Exception as e:
                logger.error(f"Error creating plot: {e}")
                blank_canvas = FigureCanvasQTAgg(fig)  # type: ignore[no-untyped-call]
                self.plot_tab_widget.addTab(blank_canvas, "Error")

        with MatplotlibFigureContext(fig_size=self.parameters.fig_size) as (fig, ax):
            try:
                fig, ax = self.create_third_plot()
                canvas = FigureCanvasQTAgg(fig)  # type: ignore[no-untyped-call]
                toolbar = NavigationToolbar2QT(canvas, self)  # type: ignore[no-untyped-call]

                # handler = MatplotlibInteractionHandler(canvas, )

                layout.addWidget(canvas)
                layout.addWidget(toolbar)

            except Exception as e:
                logger.error(f"Error creating plot: {e}")
                blank_canvas = FigureCanvasQTAgg(fig)  # type: ignore[no-untyped-call]
                self.plot_tab_widget.addTab(blank_canvas, "Error")

            widget.setLayout(layout)
            self.plot_tab_widget.addTab(widget, "SecondPlot")

    def update_tab_widget(self) -> None:
        with BlockSignalsContext(self.plot_tab_widget):
            clear_tabs(self.plot_tab_widget)
            self.update_first_tab()
            self.update_second_tab()
