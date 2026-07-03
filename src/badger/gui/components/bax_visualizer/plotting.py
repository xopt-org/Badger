"""Matplotlib-based plotting widget for visualizing BAX virtual measurements."""

import logging
from typing import TYPE_CHECKING, Optional

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.backends.backend_qt import NavigationToolbar2QT
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt5.QtWidgets import (
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from xopt.generators.bayesian.bax_generator import BaxGenerator

from badger.gui.components.extension_utilities import (
    clear_tabs,
)
from badger.utils import BlockSignalsContext
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

    def get_plot_results_keys(self) -> list[str]:
        algorithm_type = self.generator.algorithm.name
        if algorithm_type == "grid_optimize":
            plot_options_dict = {
                "objective": self.parameters.tab_1.grid_optimize.objective
            }

        elif algorithm_type == "emittance":
            plot_options_dict = {
                "emittance_x": self.parameters.tab_1.emittance.emittance_x,
                "emittance_y": self.parameters.tab_1.emittance.emittance_y,
                "bmag_x": self.parameters.tab_1.emittance.bmag_x,
                "bmag_y": self.parameters.tab_1.emittance.bmag_y,
            }
        elif algorithm_type == "pathwise_solenoid_alignment":
            plot_options_dict = {
                "misalignment_x": self.parameters.tab_1.pathwise_solenoid_alignment.misalignment_x,
                "misalignment_y": self.parameters.tab_1.pathwise_solenoid_alignment.misalignment_y,
            }
        else:
            raise ValueError(f"Unsupported algorithm type: {algorithm_type}")

        result_keys = [key for key, enabled in plot_options_dict.items() if enabled]

        if len(result_keys) == 0:
            logger.warning(
                "No results keys selected for plotting. Please enable at least one plot option."
            )

        return result_keys

    def create_first_plot(self) -> tuple[Figure, Axes]:
        logger.debug("Creating first plot")

        selected_variable_names = [
            self.parameters.variables[self.parameters.variable_idx_x]
        ]
        if self.parameters.include_y:
            selected_variable_names.append(
                self.parameters.variables[self.parameters.variable_idx_y]
            )

        results_keys = self.get_plot_results_keys()
        logger.debug(f"Results keys for plotting: {results_keys}")

        logger.debug(f"Results file: {self.generator.algorithm_results_file}")
        fig, ax = visualize_virtual_measurement_result(
            self.generator,
            variable_names=selected_variable_names,
            idx=0,
            reference_point=None,  # type: ignore[arg-type]
            n_grid=self.parameters.tab_1.n_grid,
            n_samples=self.parameters.tab_1.n_samples,
            show_observations=True,
            result_keys=results_keys,
        )
        return fig, ax

    def create_second_plot(self) -> tuple[Figure, Axes]:
        logger.debug("Creating second plot")
        logger.debug(f"Results file: {self.generator.algorithm_results_file}")
        fig, ax = plot_bax_objective_convergence(
            self.generator,
        )
        return fig, ax

    def create_third_plot(self) -> tuple[Figure, Axes]:
        logger.debug("Creating third plot")
        logger.debug(f"Results file: {self.generator.algorithm_results_file}")
        fig, ax = plot_bax_input_convergence(
            self.generator,
        )
        return fig, ax

    def _build_plot_widget(self, fig: Figure, add_stretch: bool = False) -> QWidget:
        """Wrap a figure in a canvas + toolbar, constraining the canvas height
        to the figure's natural pixel size.

        Matplotlib canvases default to an Expanding/Expanding size policy, which
        is what causes a short single plot to be stretched to match a taller
        tab. Fixing the vertical policy and a minimum height keeps each plot at
        its intended aspect ratio.
        """
        canvas = FigureCanvasQTAgg(fig)  # type: ignore[no-untyped-call]
        toolbar = NavigationToolbar2QT(canvas, self)  # type: ignore[no-untyped-call]

        width_inches, height_inches = fig.get_size_inches()
        dpi = fig.get_dpi()
        canvas.setMinimumSize(int(width_inches * dpi), int(height_inches * dpi))
        canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(toolbar)
        layout.addWidget(canvas)
        if add_stretch:
            # Absorb any extra vertical space so the canvas keeps its height
            # instead of stretching to fill the tab.
            layout.addStretch(1)
        return widget

    @staticmethod
    def _scrollable(content: QWidget) -> QScrollArea:
        """Place tab content in a scroll area so plots taller than the visible
        area scroll instead of forcing the whole extension window to grow."""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(content)
        return scroll_area

    def update_first_tab(self) -> None:
        try:
            fig, _ = self.create_first_plot()
            content = self._build_plot_widget(fig, add_stretch=True)
            self.plot_tab_widget.addTab(self._scrollable(content), "FirstPlot")
            plt.close(fig)
        except Exception as e:
            logger.error(f"Error creating plot: {e}")
            self.plot_tab_widget.addTab(QWidget(), "Error")

    def update_second_tab(self) -> None:
        content = QWidget()
        layout = QVBoxLayout(content)

        for create_plot in (self.create_second_plot, self.create_third_plot):
            try:
                fig, _ = create_plot()
                layout.addWidget(self._build_plot_widget(fig))
                plt.close(fig)
            except Exception as e:
                logger.error(f"Error creating plot: {e}")

        # Keep the plots top-aligned at their natural height; the scroll area
        # handles the case where their combined height exceeds the viewport.
        layout.addStretch(1)
        self.plot_tab_widget.addTab(self._scrollable(content), "SecondPlot")

    def update_tab_widget(self) -> None:
        with BlockSignalsContext(self.plot_tab_widget):
            clear_tabs(self.plot_tab_widget)
            self.update_first_tab()
            self.update_second_tab()
        self.plot_tab_widget.setCurrentIndex(self.parameters.active_tab)
