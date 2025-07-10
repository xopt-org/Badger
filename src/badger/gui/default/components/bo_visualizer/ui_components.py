from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QGroupBox,
    QTableWidget,
    QTableWidgetItem,
    QSpinBox,
    QPushButton,
    QCheckBox,
    QHeaderView,
)
from PyQt5.QtCore import Qt

from badger.gui.default.components.bo_visualizer.types import ConfigurableOptions
from badger.gui.default.components.extension_utilities import (
    BlockSignalsContext,
    HandledException,
    to_precision_float,
)

import logging


logger = logging.getLogger(__name__)


class UIComponents:
    variables: list[str] = []

    def __init__(
        self,
        default_parameters: ConfigurableOptions,
    ):
        self.variable_checkboxes = {}
        self.ref_inputs: list[QTableWidgetItem] = []
        self.reference_table = None  # Will be initialized later
        self.best_point_display = QLabel("")  # Will be initialized later
        self.set_best_reference_point_button = QPushButton("Set Best Reference Point")

        # Initialize other UI components
        self.update_button = QPushButton("Update")
        self.x_axis_combo = QComboBox()
        self.y_axis_combo = QComboBox()
        self.y_axis_checkbox = QCheckBox("Include Variable 2")
        self.acq_func_checkbox = QCheckBox("Show Acquisition Function")
        self.show_samples_checkbox = QCheckBox("Show Samples")
        self.show_prior_mean_checkbox = QCheckBox("Show Prior Mean")
        self.show_feasibility_checkbox = QCheckBox("Show Feasibility")
        self.n_grid = QSpinBox()

        include_variable_2 = default_parameters["include_variable_2"]
        show_prior_mean = default_parameters["plot_options"]["show_prior_mean"]
        show_feasibility = default_parameters["plot_options"]["show_feasibility"]
        show_samples = default_parameters["plot_options"]["show_samples"]
        show_acq_func = default_parameters["plot_options"]["show_acq_func"]
        n_grid = default_parameters["plot_options"]["n_grid"]
        n_grid_range = default_parameters["plot_options"]["n_grid_range"]

        # Set default parameters
        self.y_axis_checkbox.setChecked(include_variable_2)
        self.acq_func_checkbox.setChecked(show_acq_func)
        self.show_samples_checkbox.setChecked(show_samples)
        self.show_prior_mean_checkbox.setChecked(show_prior_mean)
        self.show_feasibility_checkbox.setChecked(show_feasibility)
        self.n_grid.setRange(n_grid_range[0], n_grid_range[1])
        self.n_grid.setValue(n_grid)

        # Initialize layouts
        self.variable_checkboxes_layout = None

    def create_variable_checkboxes(self):
        group_box = QGroupBox("Select Variables")
        layout = self.variable_checkboxes_layout or QVBoxLayout()
        group_box.setLayout(layout)
        return group_box

    def create_axis_layout(self):
        layout = QVBoxLayout()

        x_layout = QHBoxLayout()
        x_label = QLabel("Variable 1:")
        x_axis_label = QLabel("X-axis")
        x_layout.addWidget(x_label)
        x_layout.addWidget(self.x_axis_combo)
        x_layout.addWidget(x_axis_label)

        y_layout = QHBoxLayout()
        y_label = QLabel("Variable 2:")
        y_axis_label = QLabel("Y-axis")
        y_layout.addWidget(y_label)
        y_layout.addWidget(self.y_axis_combo)
        y_layout.addWidget(y_axis_label)

        include_var2_layout = QHBoxLayout()
        include_var2_layout.addWidget(self.y_axis_checkbox)

        layout.addLayout(x_layout)
        layout.addLayout(y_layout)
        layout.addLayout(include_var2_layout)

        return layout

    def initialize_ui_components(
        self,
        configurable_options: ConfigurableOptions,
    ):
        self.populate_reference_table(
            configurable_options["variables"],
            configurable_options["reference_points"],
        )

    def initialize_variables(
        self,
        configurable_options: ConfigurableOptions,
        vocs_variables: dict[str, tuple[float, float]],
    ):
        """Initialize the variable checkboxes with the provided variable names."""
        # Initialize the parameters with the routine's variables
        configurable_options["reference_points_range"] = vocs_variables
        configurable_options["reference_points"] = {
            var: to_precision_float(
                (vocs_variables[var][1] - vocs_variables[var][0]) / 2.0
            )
            for var in vocs_variables
        }

    def create_reference_inputs(self):
        group_box = QGroupBox("Reference Points")
        layout = QVBoxLayout()

        self.reference_table = QTableWidget()
        self.reference_table.setColumnCount(2)
        self.reference_table.setHorizontalHeaderLabels(["Variable", "Ref. Point"])
        horizontal_header = self.reference_table.horizontalHeader()
        if horizontal_header is not None:
            horizontal_header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

        layout.addWidget(self.reference_table)
        layout.addWidget(self.set_best_reference_point_button)
        layout.addWidget(self.best_point_display)
        group_box.setLayout(layout)
        return group_box

    def populate_reference_table(
        self,
        variables: list[str],
        reference_points: dict[str, float],
    ):
        """Populate the reference table based on the current vocs variable names."""

        logger.debug("Populating reference table")
        if self.reference_table is None:
            raise HandledException(ValueError, "Reference Table is None")

        with BlockSignalsContext(self.reference_table):
            self.reference_table.setRowCount(len(variables))
            self.ref_inputs = []

            for i, var_name in enumerate(variables):
                variable_item = QTableWidgetItem(var_name)
                itemIsEditable = Qt.ItemFlag.ItemIsEditable

                variable_item.setFlags(
                    variable_item.flags() & ~Qt.ItemFlags(itemIsEditable)
                )
                self.reference_table.setItem(i, 0, variable_item)

                value = reference_points[var_name]

                reference_point_item = QTableWidgetItem(str(value))
                self.ref_inputs.append(reference_point_item)
                self.reference_table.setItem(i, 1, reference_point_item)

    def create_options_section(self):
        group_box = QGroupBox("Plot Options")
        layout = QVBoxLayout()

        layout.addWidget(self.acq_func_checkbox)
        layout.addWidget(self.show_samples_checkbox)
        layout.addWidget(self.show_prior_mean_checkbox)
        layout.addWidget(self.show_feasibility_checkbox)

        grid_layout = QHBoxLayout()
        n_grid_label = QLabel("No. of Grid Points:")
        grid_layout.addWidget(n_grid_label)
        grid_layout.addWidget(self.n_grid)

        layout.addLayout(grid_layout)
        group_box.setLayout(layout)
        return group_box

    def create_buttons(self):
        layout = QHBoxLayout()
        self.update_button = QPushButton("Update")

        layout.addWidget(self.update_button)

        self.update_button.setObjectName("update_button")

        return layout

    def update_variables(
        self,
        configurable_options: ConfigurableOptions,
    ):
        with BlockSignalsContext([self.x_axis_combo, self.y_axis_combo]):
            self.x_axis_combo.clear()
            self.y_axis_combo.clear()

            for variable_name in configurable_options["variables"]:
                self.x_axis_combo.addItem(variable_name)
                self.y_axis_combo.addItem(variable_name)

            self.x_axis_combo.setCurrentIndex(configurable_options["variable_1"])
            self.y_axis_combo.setCurrentIndex(configurable_options["variable_2"])

        self.populate_reference_table(
            configurable_options["variables"],
            configurable_options["reference_points"],
        )
