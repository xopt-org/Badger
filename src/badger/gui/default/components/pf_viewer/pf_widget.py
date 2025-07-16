import time
from typing import Optional

from PyQt5.QtWidgets import (
    QWidget,
    QSizePolicy,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QComboBox,
    QCheckBox,
    QLabel,
    QGroupBox,
    QTabWidget,
)

from PyQt5.QtCore import Qt
from badger.gui.default.components.plot_event_handlers import (
    MatplotlibInteractionHandler,
)
from badger.gui.default.components.pf_viewer.types import PFUI, ConfigurableOptions
from badger.routine import Routine

from badger.utils import create_archive_run_filename
from matplotlib.axes import Axes
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.ticker import MaxNLocator
from matplotlib.backends.backend_qt import (
    NavigationToolbar2QT as NavigationToolbar,
)
import pandas as pd
from torch import Tensor

from xopt.generators.bayesian.mobo import MOBOGenerator

from badger.gui.default.components.pf_viewer.types import (
    PFUIWidgets,
    PFUILayouts,
)

from badger.gui.default.components.analysis_widget import AnalysisWidget

from badger.gui.default.components.extension_utilities import (
    BlockSignalsContext,
    HandledException,
    MatplotlibFigureContext,
    signal_logger,
    requires_update,
    clear_tabs,
    clear_layout,
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


class ParetoFrontWidget(AnalysisWidget):
    generator: MOBOGenerator
    parameters: ConfigurableOptions = DEFAULT_PARAMETERS

    hypervolume_history: pd.DataFrame = pd.DataFrame()
    pf_1: Optional[Tensor] = None
    pf_2: Optional[Tensor] = None
    pf_mask: Optional[Tensor] = None
    plot_size: tuple[float, float] = (8, 6)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent=parent)

        self.create_ui()
        self.setWindowTitle("Pareto Front Viewer")
        self.setMinimumWidth(1200)

    def isValidRoutine(self, routine: Routine) -> None:
        if len(routine.vocs.objective_names) < 2:
            raise HandledException(
                ValueError,
                "The routine must have at least two objectives to visualize the Pareto front.",
            )

    def reset_widget(self) -> None:
        """
        Reset the widget to its initial state.
        This method should be called when the routine is changed or when the widget needs to be reset.
        """
        logger.debug("Resetting ParetoFrontWidget")
        self.hypervolume_history = pd.DataFrame()
        self.pf_1 = None
        self.pf_2 = None
        self.pf_mask = None

    def requires_reinitialization(self) -> bool:
        # Check if the extension needs to be reinitialized
        logger.debug("Checking if extension needs to be reinitialized")

        archive_name = create_archive_run_filename(self.routine)

        if not self.initialized:
            logger.debug("Reset - Extension never initialized")
            self.initialized = True
            self.routine_identifier = archive_name
            self.reset_widget()
            self.setup_connections()
            return True

        if self.routine_identifier != archive_name:
            logger.debug("Reset - Routine name has changed")
            self.routine_identifier = archive_name
            self.reset_widget()
            return True

        if self.routine.data is None:
            logger.debug("Reset - No data available")
            self.reset_widget()
            return True

        previous_len = self.df_length
        self.df_length = len(self.routine.data)
        new_length = self.df_length

        if previous_len > new_length:
            logger.debug("Reset - Data length is smaller")
            self.reset_widget()
            self.df_length = float("inf")
            return True

        return False

    def update_plots(
        self,
        requires_rebuild: bool = False,
        interval: int = 1000,
    ) -> None:
        if not requires_update(self.last_updated, interval, requires_rebuild):
            logging.debug("Skipping plot update")
            return

        self.update_pareto_front_plot()

        self.update_hypervolume_plot()

        # Update the last updated time
        self.last_updated = time.time()

    def setup_connections(self):
        self.ui["components"]["update"].clicked.connect(
            lambda: signal_logger("Update button clicked")(
                lambda: self.on_button_click()
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

    def initialize_widget(self) -> None:
        # Setup the variable dropdowns
        variable_names = self.routine.vocs.variable_names
        objective_names = self.routine.vocs.objective_names

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
            raise HandledException(ValueError, "Invalid plot tab")

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
            raise HandledException(ValueError, "Invalid plot tab")

        self.update_pareto_front_plot()

    def on_button_click(self):
        self.update_extension(self.routine, True)

    def update_ui(self):
        self.update_plots(requires_rebuild=True)

    def update_pareto_front_plot(
        self,
    ):
        self.update_pareto_front()

        plot_tab_widget = self.ui["components"]["plot"]["pareto"]

        with BlockSignalsContext(plot_tab_widget):
            clear_tabs(plot_tab_widget)

            with MatplotlibFigureContext(fig_size=self.plot_size) as (fig, ax):
                try:
                    fig, ax = self.create_pareto_plot(fig, ax)
                    canvas = FigureCanvas(fig)
                    toolbar = NavigationToolbar(canvas, self)

                    handler = MatplotlibInteractionHandler(
                        canvas, self.parameters, self.routine, self.update_extension
                    )
                    handler.connect_events()

                    widget = QWidget()

                    layout = QVBoxLayout(widget)
                    layout.addWidget(canvas)
                    layout.addWidget(toolbar)

                    widget.setLayout(layout)

                    ax.set_title("Data Points")
                    plot_tab_widget.addTab(widget, "Variable Space")
                except ValueError:
                    logging.error("No data points available for Variable Space")
                    blank_canvas = FigureCanvas(fig)
                    plot_tab_widget.addTab(blank_canvas, "Variable Space")

            with MatplotlibFigureContext(fig_size=self.plot_size) as (fig, ax):
                try:
                    fig, ax = self.create_pareto_plot(fig, ax)
                    canvas = FigureCanvas(fig)
                    toolbar = NavigationToolbar(canvas, self)

                    handler = MatplotlibInteractionHandler(
                        canvas, self.parameters, self.routine, self.update_extension
                    )
                    handler.connect_events()

                    widget = QWidget()

                    layout = QVBoxLayout(widget)
                    layout.addWidget(canvas)
                    layout.addWidget(toolbar)

                    widget.setLayout(layout)

                    ax.set_title("Pareto Front")
                    plot_tab_widget.addTab(widget, "Objective Space")
                except ValueError:
                    logging.error("No data points available for Objective Space")
                    blank_canvas = FigureCanvas(fig)
                    plot_tab_widget.addTab(blank_canvas, "Objective Space")

            plot_tab_widget.setCurrentIndex(self.parameters["plot_tab"])

        plot_tab_widget.updateGeometry()
        plot_tab_widget.adjustSize()

    def update_hypervolume_plot(
        self,
    ):
        self.update_hypervolume()

        plot_hypervolume = self.ui["components"]["plot"]["hypervolume"]

        with BlockSignalsContext(plot_hypervolume):
            clear_layout(plot_hypervolume)

            with MatplotlibFigureContext(fig_size=self.plot_size) as (fig, ax):
                try:
                    fig, ax = self.create_hypervolume_plot(fig, ax)
                    canvas = FigureCanvas(fig)
                    plot_hypervolume.addWidget(canvas)
                except ValueError:
                    logging.error("No data points available for Hypervolume")
                    blank_canvas = FigureCanvas(fig)
                    plot_hypervolume.addWidget(blank_canvas)

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
            raise HandledException(
                ValueError,
                "Invalid plot index for current tab when creating pareto plot",
            )

        if self.pf_mask is None or self.pf_1 is None or self.pf_2 is None:
            logging.error("No pareto front data available")
            # Return empty plot, does not raise an error
            return fig, ax

        raw_data = self.generator.data

        if raw_data is None or len(raw_data) == 0:
            raise HandledException(
                ValueError, "No raw data available when creating pareto plot"
            )

        if current_tab == 0:
            data_points = self.pf_1
        elif current_tab == 1:
            data_points = self.pf_2
        else:
            raise HandledException(
                ValueError,
                "Invalid plot index for current tab when creating pareto plot",
            )

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
                    picker=True,
                    pickradius=5,
                )

        pf_colors = [colors[i] for i in data_indices]

        ax.scatter(
            data_points[:, x_var_index],
            data_points[:, y_var_index],
            c=pf_colors,
            picker=True,
            pickradius=5,
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
            raise HandledException(
                ValueError, "No data points available for Hypervolume"
            )
        # Extract the x and y coordinates from the data points
        x = data_points["iteration"].values
        y = data_points["hypervolume"].values
        # Create a scatter plot
        ax.plot(
            x,
            y,
            color="black",
            picker=True,
            pickradius=5,
        )
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        # Set the x and y axis labels
        ax.set_xlabel("Iterations")
        ax.set_ylabel("Hypervolume")
        # Set the title of the plot
        ax.set_title("Hypervolume")

        return fig, ax

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
