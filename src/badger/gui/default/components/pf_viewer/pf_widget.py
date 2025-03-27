from functools import wraps
import time
from typing import Callable, Optional, cast, ParamSpec
from types import TracebackType
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QLayout,
    QPushButton,
    QComboBox,
    QRadioButton,
    QLabel,
    QGroupBox,
    QTabWidget,
)

from PyQt5.QtCore import Qt
from badger.gui.default.components.pf_viewer.types import PFUI, ConfigurableOptions
from badger.routine import Routine

from matplotlib.axes import Axes
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from xopt.generators.bayesian.mobo import MOBOGenerator

from badger.gui.default.components.pf_viewer.types import (
    PFUIWidgets,
    PFUILayouts,
)

import logging

logger = logging.getLogger(__name__)


DEFAULT_PARAMETERS: ConfigurableOptions = {
    "plot_options": {
        "show_samples": True,
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


class MatplotlibFigureContext:
    def __init__(self):
        self.fig = Figure()
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
    df_length: int
    correct_generator: bool
    last_updated: Optional[float] = None
    routine_identifier: str = ""
    parameters: ConfigurableOptions = DEFAULT_PARAMETERS
    initialized: bool = False

    plot_ittr_colors = ("#648FFF", "#FFB000")

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent=parent)

        self.create_ui()

    def isValidRoutine(self, routine: Routine):
        if routine.vocs.objective_names is None:
            logging.error("No objective names")
            return False
        if len(routine.vocs.objective_names) < 2:
            logging.error("Invalid number of objectives")
            return False

        return True

    def setup_connections(self, routine: Routine):
        self.ui["components"]["update"].clicked.connect(
            lambda: signal_logger("Update button clicked")(
                lambda: self.update_plot(routine)
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

    def create_ui(self):
        update_button = QPushButton("Update")
        variable_1_combo = QComboBox()
        variable_2_combo = QComboBox()
        sample_checkbox = QRadioButton("Show Samples")

        components: PFUIWidgets = {
            "variables": {
                "variable_1": variable_1_combo,
                "variable_2": variable_2_combo,
            },
            "options": {
                "sample_checkbox": sample_checkbox,
            },
            "update": update_button,
            "plot": QTabWidget(),
        }

        layouts: PFUILayouts = {
            "main": QHBoxLayout(),
            "settings": QVBoxLayout(),
            "plot": QVBoxLayout(),
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
        variable_1_layout.addWidget(QLabel("Variable 1"))
        variables_layout.addWidget(variable_1_combo)

        variable_2_layout = QHBoxLayout()
        variable_2_layout.addWidget(QLabel("Variable 2"))
        variables_layout.addWidget(variable_2_combo)

        variables_layout.addLayout(variable_1_layout)
        variables_layout.addLayout(variable_2_layout)

        variables_group = QGroupBox("Variables")
        variables_group.setLayout(variables_layout)

        settings_layout.addWidget(variables_group)

        # Options layout
        options_layout = self.ui["layouts"]["options"]

        sample_checkbox = self.ui["components"]["options"]["sample_checkbox"]
        sample_checkbox.setChecked(self.parameters["plot_options"]["show_samples"])

        options_layout.addWidget(sample_checkbox)

        settings_layout.addLayout(options_layout)

        # Update layout

        update_button = self.ui["components"]["update"]

        settings_layout.addWidget(update_button)

        main_layout.addLayout(settings_layout)

        # Right side of the layout
        plot_layout = self.ui["layouts"]["plot"]
        plot_tab_widget = self.ui["components"]["plot"]
        plot_tab_widget.setCurrentIndex(self.parameters["plot_tab"])

        plot_layout.addWidget(plot_tab_widget)

        main_layout.addLayout(plot_layout)

        self.setLayout(main_layout)

    def initialize_ui(self):
        routine = self.routine

        # Setup the variable dropdowns
        variable_names = routine.vocs.variable_names
        objective_names = routine.vocs.objective_names

        if variable_names is None:
            logging.error("No variable names")
            return
        if objective_names is None:
            logging.error("No objective names")
            return

        self.parameters["variables"] = variable_names
        self.parameters["objectives"] = objective_names

        variable_1_combo = self.ui["components"]["variables"]["variable_1"]
        variable_2_combo = self.ui["components"]["variables"]["variable_2"]

        variable_1_combo.blockSignals(True)
        variable_2_combo.blockSignals(True)

        variable_1_combo.clear()
        variable_2_combo.clear()

        for variable_name in variable_names:
            variable_1_combo.addItem(variable_name)
            variable_2_combo.addItem(variable_name)

        variable_1_combo.setCurrentIndex(self.parameters["variable_1"])
        variable_2_combo.setCurrentIndex(self.parameters["variable_2"])

        variable_1_combo.blockSignals(False)
        variable_2_combo.blockSignals(False)

    def on_variable_change(self):
        self.parameters["variable_1"] = self.ui["components"]["variables"][
            "variable_1"
        ].currentIndex()
        self.parameters["variable_2"] = self.ui["components"]["variables"][
            "variable_2"
        ].currentIndex()
        self.parameters["plot_tab"] = self.ui["components"]["plot"].currentIndex()

        self.update_ui()

    def update_ui(self):
        self.create_plot(self.generator, requires_rebuild=True)

    def clear_tabs(self, tab_widget: QTabWidget):
        max_index = tab_widget.count()
        tab_widget.blockSignals(True)
        for i in range(max_index - 1, -1, -1):
            tab_widget.removeTab(i)
        tab_widget.blockSignals(False)

    def create_plot(
        self, generator: MOBOGenerator, requires_rebuild=False, interval=1000
    ):
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

        plot_tab_widget = self.ui["components"]["plot"]

        self.clear_tabs(plot_tab_widget)

        with MatplotlibFigureContext() as (fig, ax):
            fig0, ax0 = self.create_pareto_plot(fig, ax, generator, 0)
            canvas0 = FigureCanvas(fig0)

            ax0.set_title("Data Points")
            plot_tab_widget.addTab(canvas0, "Variable Space")

        with MatplotlibFigureContext() as (fig, ax):
            fig1, ax1 = self.create_pareto_plot(fig, ax, generator, 1)
            canvas1 = FigureCanvas(fig1)

            ax1.set_title("Pareto Front")
            plot_tab_widget.addTab(canvas1, "Objective Space")

        plot_tab_widget.setCurrentIndex(self.parameters["plot_tab"])

        plot_layout = self.ui["layouts"]["plot"]
        plot_layout.addWidget(plot_tab_widget)

        # Update the last updated time
        self.last_updated = time.time()

    def create_pareto_plot(
        self, fig: Figure, ax: Axes, generator: MOBOGenerator, plot_index: int
    ):
        if generator.vocs.objective_names is None:
            logging.error("No objective names")
            raise ValueError("No objective names")
        if generator.vocs.variable_names is None:
            logging.error("No variable names")
            raise ValueError("No variable names")

        logger.debug(f"x: {self.parameters['variable_1']}")
        logger.debug(f"y: {self.parameters['variable_2']}")

        if plot_index == 0:
            x_axis = self.parameters["variable_1"]
            y_axis = self.parameters["variable_2"]

            x_var_name = generator.vocs.variable_names[x_axis]
            y_var_name = generator.vocs.variable_names[y_axis]
        elif plot_index == 1:
            x_axis = self.parameters["objective_1"]
            y_axis = self.parameters["objective_2"]

            x_var_name = generator.vocs.objective_names[x_axis]
            y_var_name = generator.vocs.objective_names[y_axis]
        else:
            logging.error("Invalid plot index")
            raise ValueError("Invalid plot index")

        pareto_front = generator.get_pareto_front()

        if pareto_front[0] is None or pareto_front[1] is None:
            logging.error("No pareto front")
            raise ValueError("No pareto front")

        raw_data = generator.data

        if raw_data is not None:
            x = raw_data[f"{x_var_name}"]
            y = raw_data[f"{y_var_name}"]

            if len(x) > 0 and len(y) > 0:
                ax.scatter(
                    x,
                    y,
                    color="black",
                )

        data_points = pareto_front[plot_index]
        num_of_points = len(data_points)

        color_map = LinearSegmentedColormap.from_list(
            "custom", self.plot_ittr_colors, N=num_of_points
        )

        for i, data_point in enumerate(data_points):
            color = (
                color_map(i / (num_of_points - 1))
                if num_of_points > 1
                else color_map(0)
            )
            ax.scatter(data_point[0], data_point[1], color=color)

        ax.set_xlabel(x_var_name)
        ax.set_ylabel(y_var_name)

        return fig, ax

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

    def requires_reinitialization(self):
        # Check if the extension needs to be reinitialized
        logger.debug("Checking if extension needs to be reinitialized")

        if not self.initialized:
            logger.debug("Reset - Extension never initialized")
            self.initialized = True
            return True

        if self.routine_identifier != self.routine.name:
            logger.debug("Reset - Routine name has changed")
            self.identifier = self.routine.name
            return True

        if self.routine.data is None:
            logger.debug("Reset - No data available")
            return True

        previous_len = self.df_length
        self.df_length = len(self.routine.data)
        new_length = self.df_length

        if previous_len > new_length:
            logger.debug("Reset - Data length is the same or smaller")
            self.df_length = int("inf")
            return True

        return False

    def update_plot(self, routine: Routine):
        self.update_routine(routine)

        if not self.isValidRoutine(self.routine):
            logging.error("Invalid routine")
            return

        if not isinstance(self.generator, MOBOGenerator):
            logging.error("Invalid generator")
            return

        if self.requires_reinitialization():
            self.setup_connections(self.routine)
            self.initialize_ui()

        self.create_plot(self.generator)

        hypervolume = self.create_hypervolume_plot(self.generator)
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

        if generator.data is None:
            logger.error("No data available in generator")
            QMessageBox.critical(
                self,
                "No data available",
                "No data available in generator",
            )
            return

        self.df_length = len(generator.data)
        self.generator = generator
