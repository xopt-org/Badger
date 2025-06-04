from functools import wraps
import time
from typing import Callable, Optional, cast, ParamSpec, Iterable
from types import TracebackType
from PyQt5.QtWidgets import (
    QWidget,
    QSizePolicy,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QLayout,
    QGridLayout,
    QPushButton,
    QComboBox,
    QCheckBox,
    QLabel,
    QGroupBox,
    QTabWidget,
)

from PyQt5.QtCore import Qt
from badger.gui.default.components.pf_viewer.types import PFUI, ConfigurableOptions
from badger.routine import Routine

from badger.utils import create_archive_run_filename
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import MaxNLocator
import pandas as pd
from torch import Tensor

from xopt.generators.bayesian.mobo import MOBOGenerator

from badger.gui.default.components.pf_viewer.types import (
    PFUIWidgets,
    PFUILayouts,
)

import logging

logger = logging.getLogger(__name__)


DEFAULT_PARAMETERS: ConfigurableOptions = {
    "plot_options": {
        "show_only_pareto_front": False,
    },
    "variable_1": 0,
    "variable_2": 1,
    "variables": [],
    "objectives": [],
    "objective_1": 0,
    "objective_2": 1,
    "plot_tab": 0,
}

Param = ParamSpec("Param")


def signal_logger(text: str):
    def decorator(fn: Callable[Param, None]) -> Callable[Param, None]:
        @wraps(fn)
        def wrapper(*args: Param.args, **kwargs: Param.kwargs):
            logger.debug(f"{text}")
            return fn(*args, **kwargs)

        return wrapper

    return decorator


class BlockSignalsContext:
    widgets: Iterable[QWidget | QLayout]

    def __init__(self, widgets: QWidget | QLayout | Iterable[QWidget | QLayout]):
        if isinstance(widgets, Iterable):
            self.widgets = widgets
        else:
            self.widgets = [widgets]

    def __enter__(self):
        for widget in self.widgets:
            if widget.signalsBlocked():
                logger.warning(
                    f"Signals already blocked for {widget} when entering context. Nesting BlockSignalsContext is not recommended as blockSignals is set to False upon exiting the context. This may lead to unexpected behavior if the widget is used again from within another BlockSignalsContext."
                )
            widget.blockSignals(True)

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        exc_traceback: Optional[TracebackType],
    ):
        for widget in self.widgets:
            if not widget.signalsBlocked():
                logger.warning(
                    f"Signals not blocked for {widget} when exiting context. Nesting BlockSignalsContext is not recommended as blockSignals is set to False upon exiting the context. This may lead to unexpected behavior if the widget is used again from within another BlockSignalsContext."
                )
            widget.blockSignals(False)


class MatplotlibFigureContext:
    def __init__(self, fig_size: tuple[float, float] | None = None):
        self.fig_size = fig_size
        self.fig = Figure(figsize=self.fig_size)
        self.ax = self.fig.add_subplot()

    def __enter__(self):
        return self.fig, self.ax

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        exc_traceback: Optional[TracebackType],
    ):
        plt.close(self.fig)


class ParetoFrontWidget(QWidget):
    routine: Routine
    generator: MOBOGenerator
    df_length: float = float("inf")
    correct_generator: bool
    last_updated: Optional[float] = None
    routine_identifier: str = ""
    hypervolume_history: pd.DataFrame = pd.DataFrame()
    pf_1: Optional[Tensor] = None
    pf_2: Optional[Tensor] = None
    pf_mask: Optional[Tensor] = None
    parameters: ConfigurableOptions = DEFAULT_PARAMETERS
    initialized: bool = False
    plot_size: tuple[float, float] = (8, 6)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent=parent)

        self.create_ui()
        self.setWindowTitle("Pareto Front Viewer")
        self.setMinimumWidth(1200)

    def isValidRoutine(self, routine: Routine):
        if len(routine.vocs.objective_names) < 2:
            logging.error("Invalid number of objectives")
            return False

        return True

    def setup_connections(self, routine: Routine):
        self.ui["components"]["update"].clicked.connect(
            lambda: signal_logger("Update button clicked")(
                lambda: self.update_plot(routine, requires_rebuild=True)
            )()
        )

        self.ui["components"]["variables"]["variable_1"].currentIndexChanged.connect(
            lambda: signal_logger("Variable 1 has changed")(
                lambda: self.on_variable_change()
            )()
        )
        self.ui["components"]["variables"]["variable_2"].currentIndexChanged.connect(
            lambda: signal_logger("Variable 2 has changed")(
                lambda: self.on_variable_change()
            )()
        )

        self.ui["components"]["plot"]["pareto"].currentChanged.connect(
            lambda: signal_logger("Tab changed")(lambda: self.on_tab_change())()
        )

        self.ui["components"]["options"]["show_only_pareto_front"].clicked.connect(
            lambda: signal_logger("Sample checkbox changed")(lambda: self.update_ui())()
        )

    def create_ui(self):
        update_button = QPushButton("Update")
        variable_1_combo = QComboBox()
        variable_1_combo.setMinimumWidth(100)
        variable_2_combo = QComboBox()
        variable_2_combo.setMinimumWidth(100)
        show_only_pareto_front = QCheckBox("Show only Pareto Front")

        components: PFUIWidgets = {
            "variables": {
                "variable_1": variable_1_combo,
                "variable_2": variable_2_combo,
            },
            "options": {
                "show_only_pareto_front": show_only_pareto_front,
            },
            "update": update_button,
            "plot": {
                "pareto": QTabWidget(),
                "hypervolume": QVBoxLayout(),
            },
        }

        layouts: PFUILayouts = {
            "main": QHBoxLayout(),
            "settings": QVBoxLayout(),
            "plot": QGridLayout(),
            "options": QVBoxLayout(),
            "variables": QVBoxLayout(),
            "update": QVBoxLayout(),
        }

        self.ui: PFUI = {"components": components, "layouts": layouts}

        main_layout = self.ui["layouts"]["main"]

        # Left side of the layout
        settings_layout = self.ui["layouts"]["settings"]

        settings_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Variables layout

        variables_layout = self.ui["layouts"]["variables"]

        variable_1_layout = QHBoxLayout()
        variable_1_layout.addWidget(QLabel("X Axis"))
        variable_1_layout.addWidget(variable_1_combo)

        variable_2_layout = QHBoxLayout()
        variable_2_layout.addWidget(
            QLabel("Y Axis"), alignment=Qt.AlignmentFlag.AlignLeft
        )
        variable_2_layout.addWidget(variable_2_combo)

        variables_layout.addLayout(variable_1_layout)
        variables_layout.addLayout(variable_2_layout)

        variables_group = QGroupBox("Variables")
        variables_group.setLayout(variables_layout)

        settings_layout.addWidget(variables_group)

        # Options layout
        options_layout = self.ui["layouts"]["options"]

        show_only_pareto_front = self.ui["components"]["options"][
            "show_only_pareto_front"
        ]
        show_only_pareto_front.setChecked(
            self.parameters["plot_options"]["show_only_pareto_front"]
        )

        options_layout.addWidget(show_only_pareto_front)

        settings_layout.addLayout(options_layout)

        # Update layout

        update_button = self.ui["components"]["update"]

        settings_layout.addStretch(1)
        settings_layout.addWidget(update_button)
        settings_widget = QWidget()
        settings_widget.setLayout(settings_layout)
        settings_widget.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.Expanding
        )
        main_layout.addWidget(settings_widget)

        # Right side of the layout
        plot_layout = self.ui["layouts"]["plot"]
        plot_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        plot_tab_widget = self.ui["components"]["plot"]["pareto"]
        plot_tab_widget.setCurrentIndex(self.parameters["plot_tab"])
        plot_tab_widget.setMinimumWidth(400)

        plot_hypervolume_widget = QWidget()
        plot_hypervolume = self.ui["components"]["plot"]["hypervolume"]
        plot_hypervolume_widget.setLayout(plot_hypervolume)
        plot_hypervolume_widget.setMinimumWidth(400)
        plot_hypervolume_widget.setMaximumWidth(600)

        plot_layout.addWidget(plot_tab_widget, 0, 0, Qt.AlignmentFlag.AlignCenter)
        plot_layout.addWidget(
            plot_hypervolume_widget, 0, 1, Qt.AlignmentFlag.AlignCenter
        )

        main_layout.addLayout(plot_layout, 1)

        self.setLayout(main_layout)

    def initialize_ui(self):
        routine = self.routine

        # Setup the variable dropdowns
        variable_names = routine.vocs.variable_names
        objective_names = routine.vocs.objective_names

        self.parameters["variables"] = variable_names
        self.parameters["objectives"] = objective_names

        variable_1_combo = self.ui["components"]["variables"]["variable_1"]
        variable_2_combo = self.ui["components"]["variables"]["variable_2"]

        with BlockSignalsContext([variable_1_combo, variable_2_combo]):
            variable_1_combo.clear()
            variable_2_combo.clear()

            for variable_name in variable_names:
                variable_1_combo.addItem(variable_name)
                variable_2_combo.addItem(variable_name)

            variable_1_combo.setCurrentIndex(self.parameters["variable_1"])
            variable_2_combo.setCurrentIndex(self.parameters["variable_2"])

    def on_tab_change(self):
        self.parameters["plot_tab"] = self.ui["components"]["plot"][
            "pareto"
        ].currentIndex()
        # change x and y axis options
        x_combo = self.ui["components"]["variables"]["variable_1"]
        y_combo = self.ui["components"]["variables"]["variable_2"]

        plot_tab = self.parameters["plot_tab"]

        if plot_tab in (0, 1):
            with BlockSignalsContext([x_combo, y_combo]):
                x_combo.clear()
                y_combo.clear()

                if plot_tab == 0:
                    for variable_name in self.parameters["variables"]:
                        x_combo.addItem(variable_name)
                        y_combo.addItem(variable_name)

                    x_combo.setCurrentIndex(self.parameters["variable_1"])
                    y_combo.setCurrentIndex(self.parameters["variable_2"])
                elif plot_tab == 1:
                    for variable_name in self.parameters["objectives"]:
                        x_combo.addItem(variable_name)
                        y_combo.addItem(variable_name)
                    x_combo.setCurrentIndex(self.parameters["objective_1"])
                    y_combo.setCurrentIndex(self.parameters["objective_2"])
        else:
            logging.error("Invalid plot tab")
            raise ValueError("Invalid plot tab")

        # Update the plot
        self.update_pareto_front_plot()

    def on_variable_change(self):
        plot_tab = self.parameters["plot_tab"]
        if plot_tab == 0:
            self.parameters["variable_1"] = self.ui["components"]["variables"][
                "variable_1"
            ].currentIndex()
            self.parameters["variable_2"] = self.ui["components"]["variables"][
                "variable_2"
            ].currentIndex()
        elif plot_tab == 1:
            self.parameters["objective_1"] = self.ui["components"]["variables"][
                "variable_1"
            ].currentIndex()
            self.parameters["objective_2"] = self.ui["components"]["variables"][
                "variable_2"
            ].currentIndex()
        else:
            logging.error("Invalid plot tab")
            raise ValueError("Invalid plot tab")

        self.update_pareto_front_plot()

    def update_ui(self):
        self.create_plots(requires_rebuild=True)

    def clear_tabs(self, tab_widget: QTabWidget):
        max_index = tab_widget.count()
        for i in range(max_index - 1, -1, -1):
            tab_widget.removeTab(i)

    def update_pareto_front_plot(
        self,
    ):
        self.update_pareto_front()

        plot_tab_widget = self.ui["components"]["plot"]["pareto"]

        with BlockSignalsContext(plot_tab_widget):
            self.clear_tabs(plot_tab_widget)

            with MatplotlibFigureContext(self.plot_size) as (fig, ax):
                try:
                    fig0, ax0 = self.create_pareto_plot(fig, ax)
                    canvas0 = FigureCanvas(fig0)

                    ax0.set_title("Data Points")
                    plot_tab_widget.addTab(canvas0, "Variable Space")
                except ValueError:
                    logging.error("No data points available for Variable Space")
                    blank_canvas = FigureCanvas(fig)
                    plot_tab_widget.addTab(blank_canvas, "Variable Space")

            with MatplotlibFigureContext(self.plot_size) as (fig, ax):
                try:
                    fig1, ax1 = self.create_pareto_plot(fig, ax)
                    canvas1 = FigureCanvas(fig1)

                    ax1.set_title("Pareto Front")
                    plot_tab_widget.addTab(canvas1, "Objective Space")
                except ValueError:
                    logging.error("No data points available for Objective Space")
                    blank_canvas = FigureCanvas(fig)
                    plot_tab_widget.addTab(blank_canvas, "Objective Space")

            plot_tab_widget.setCurrentIndex(self.parameters["plot_tab"])

    def update_hypervolume_plot(
        self,
    ):
        self.update_hypervolume()

        plot_hypervolume = self.ui["components"]["plot"]["hypervolume"]

        with BlockSignalsContext(plot_hypervolume):
            self.clearLayout(plot_hypervolume)

            with MatplotlibFigureContext(self.plot_size) as (fig, ax):
                try:
                    fig0, ax = self.create_hypervolume_plot(fig, ax)

                    canvas = FigureCanvas(fig0)
                    plot_hypervolume.addWidget(canvas)
                except ValueError:
                    logging.error("No data points available for Hypervolume")
                    blank_canvas = FigureCanvas(fig)
                    plot_hypervolume.addWidget(blank_canvas)

    def create_plots(
        self,
        requires_rebuild: bool = False,
        interval: int = 1000,
    ):
        # Check if the plot was updated recently
        if self.last_updated is not None and not requires_rebuild:
            logger.debug(f"Time since last update: {time.time() - self.last_updated}")

            time_diff = time.time() - self.last_updated

            # If the plot was updated less than 1 second ago, skip this update
            if time_diff < interval / 1000:
                logger.debug("Skipping update")
                return

        self.update_pareto_front_plot()

        self.update_hypervolume_plot()

        # Update the last updated time
        self.last_updated = time.time()

    def create_pareto_plot(self, fig: Figure, ax: Axes):
        current_tab = self.parameters["plot_tab"]
        show_only_pareto_front = self.ui["components"]["options"][
            "show_only_pareto_front"
        ].isChecked()

        if current_tab == 0:
            x_axis = self.parameters["variable_1"]
            y_axis = self.parameters["variable_2"]

            x_var_name = self.generator.vocs.variable_names[x_axis]
            x_var_index = self.generator.vocs.variable_names.index(x_var_name)
            y_var_name = self.generator.vocs.variable_names[y_axis]
            y_var_index = self.generator.vocs.variable_names.index(y_var_name)

        elif current_tab == 1:
            x_axis = self.parameters["objective_1"]
            y_axis = self.parameters["objective_2"]

            x_var_name = self.generator.vocs.objective_names[x_axis]
            x_var_index = self.generator.vocs.objective_names.index(x_var_name)
            y_var_name = self.generator.vocs.objective_names[y_axis]
            y_var_index = self.generator.vocs.objective_names.index(y_var_name)
        else:
            logging.error("Invalid plot index")
            raise ValueError("Invalid plot index")

        if self.pf_mask is None or self.pf_1 is None or self.pf_2 is None:
            logging.error("No pareto front")
            raise ValueError("No pareto front")

        raw_data = self.generator.data

        if raw_data is None or len(raw_data) == 0:
            logging.error("No raw data available")
            raise ValueError("No raw data available")

        if current_tab == 0:
            data_points = self.pf_1
        elif current_tab == 1:
            data_points = self.pf_2
        else:
            logging.error("Invalid plot index")
            raise ValueError("Invalid plot index")

        data_indices: list[int] = [
            x for x in range(len(self.pf_mask)) if self.pf_mask[x]
        ]

        # Color bar

        num_of_points = len(raw_data)

        color_map = plt.cm.get_cmap("viridis")
        norm = Normalize(0, num_of_points - 1)

        # Map the indices to the colormap, normalizing by the total number of points
        if num_of_points > 1:
            colors = [color_map(i / (num_of_points - 1)) for i in range(num_of_points)]
        else:
            colors = [color_map(0)]

        if not show_only_pareto_front:
            x = raw_data[f"{x_var_name}"]
            y = raw_data[f"{y_var_name}"]

            if len(x) > 0 and len(y) > 0:
                ax.scatter(
                    x,
                    y,
                    c=colors,
                )

        pf_colors = [colors[i] for i in data_indices]

        ax.scatter(
            data_points[:, x_var_index],
            data_points[:, y_var_index],
            c=pf_colors,
        )

        mappable = plt.cm.ScalarMappable(cmap=color_map, norm=norm)

        fig.colorbar(
            mappable,
            ax=ax,
            orientation="vertical",
            label="Iterations",
        )

        ax.set_xlabel(x_var_name)
        ax.set_ylabel(y_var_name)

        return fig, ax

    def create_hypervolume_plot(self, fig: Figure, ax: Axes):
        data_points = self.hypervolume_history
        if len(data_points) == 0:
            raise ValueError("No data points available")
        # Extract the x and y coordinates from the data points
        x = data_points["iteration"].values
        y = data_points["hypervolume"].values
        # Create a scatter plot
        ax.plot(x, y, color="black")
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        # Set the x and y axis labels
        ax.set_xlabel("Iterations")
        ax.set_ylabel("Hypervolume")
        # Set the title of the plot
        ax.set_title("Hypervolume")

        return fig, ax

    def clearLayout(self, layout: QLayout):
        while layout.count():
            child = layout.takeAt(0)
            if child is None:
                break

            widget = child.widget()
            if widget is None:
                break

            widget.deleteLater()

    def requires_reinitialization(self):
        # Check if the extension needs to be reinitialized
        logger.debug("Checking if extension needs to be reinitialized")

        archive_name = create_archive_run_filename(self.routine)

        if not self.initialized:
            logger.debug("Reset - Extension never initialized")
            self.initialized = True
            self.routine_identifier = archive_name
            self.hypervolume_history = pd.DataFrame()
            self.pf_1 = None
            self.pf_2 = None
            self.setup_connections(self.routine)
            return True

        if self.routine_identifier != archive_name:
            logger.debug("Reset - Routine name has changed")
            self.routine_identifier = archive_name
            self.hypervolume_history = pd.DataFrame()
            self.pf_1 = None
            self.pf_2 = None
            self.pf_mask = None
            return True

        if self.routine.data is None:
            logger.debug("Reset - No data available")
            self.hypervolume_history = pd.DataFrame()
            self.pf_1 = None
            self.pf_2 = None
            self.pf_mask = None
            return True

        previous_len = self.df_length
        self.df_length = len(self.routine.data)
        new_length = self.df_length

        if previous_len > new_length:
            logger.debug("Reset - Data length is smaller")
            self.hypervolume_history = pd.DataFrame()
            self.pf_1 = None
            self.pf_2 = None
            self.pf_mask = None
            self.df_length = float("inf")
            return True

        return False

    def update_plot(self, routine: Routine, requires_rebuild: bool = False):
        if not self.update_routine(routine):
            logging.error("Failed to update routine")
            return

        if not self.isValidRoutine(self.routine):
            logging.error("Invalid routine")
            return

        if self.requires_reinitialization():
            self.initialize_ui()

        self.create_plots(requires_rebuild)

    def update_hypervolume(self):
        # Get the hypervolume from the generator
        self.generator.update_pareto_front_history()
        pareto_front_history_df = self.generator.pareto_front_history
        if pareto_front_history_df is None or len(pareto_front_history_df) == 0:
            logger.error("No hypervolume data available")
            return

        self.hypervolume_history = pareto_front_history_df

    def update_pareto_front(self):
        pf_1, pf_2, pf_mask, _ = self.generator.get_pareto_front_and_hypervolume()

        if pf_mask is None or pf_1 is None or pf_2 is None:
            logging.error("No pareto front")
            return

        self.pf_mask = pf_mask[1:]
        self.pf_1 = pf_1
        self.pf_2 = pf_2

    def update_routine(self, routine: Routine):
        logger.debug("Updating routine in Pareto Front Viewer")
        is_success = False

        self.routine = routine

        # Check if the generator is a BayesianGenerator
        if not issubclass(self.routine.generator.__class__, MOBOGenerator):
            self.correct_generator = False
            QMessageBox.critical(
                self,
                "Invalid Generator",
                f"Invalid generator type: {type(self.routine.generator)}, BO Visualizer only supports BayesianGenerator",
            )
            raise TypeError(
                f"Invalid generator type: {type(self.routine.generator)}, BO Visualizer only supports MOBOGenerator"
            )

        self.correct_generator = True

        generator = cast(MOBOGenerator, self.routine.generator)

        if generator.data is None:
            logger.error("No data available in generator")
            return is_success

        self.generator = generator
        self.df_length = len(generator.data)
        is_success = True
        return is_success
