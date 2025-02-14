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
from typing import Optional, cast

from badger.gui.default.components.bo_visualizer.types import ConfigurableOptions


from xopt import VOCS

import logging


logger = logging.getLogger(__name__)


class UIComponents:
    def __init__(
        self,
        default_parameters: ConfigurableOptions,
        vocs: Optional[VOCS] = None,
    ):
        self.vocs = vocs
        self.variable_checkboxes = {}
        self.ref_inputs: list[QTableWidgetItem] = []
        self.reference_table = None  # Will be initialized later

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

        self.ref_inputs = []

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

    def initialize_ui_components(self, configurable_options: ConfigurableOptions):
        self.populate_reference_table()

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
        group_box.setLayout(layout)
        return group_box

    def populate_reference_table(self):
        """Populate the reference table based on the current vocs variable names."""

        logger.debug("Populating reference table")
        if self.reference_table is None:
            raise Exception("Reference Table is None")

        if self.vocs is None:
            raise Exception("Vocs is None")

        self.reference_table.blockSignals(True)

        self.reference_table.setRowCount(len(self.vocs.variable_names))
        self.ref_inputs = []

        for i, var_name in enumerate(self.vocs.variable_names):
            variable_item = QTableWidgetItem(var_name)
            itemIsEditable = Qt.ItemFlag.ItemIsEditable

            variable_item.setFlags(
                variable_item.flags() & ~Qt.ItemFlags(itemIsEditable)
            )
            self.reference_table.setItem(i, 0, variable_item)

            # Set default reference point to the midpoint of variable bounds
            default_value = cast(
                float,
                (self.vocs.variables[var_name][0] + self.vocs.variables[var_name][1])
                / 2,
            )
            reference_point_item = QTableWidgetItem(str(default_value))
            self.ref_inputs.append(reference_point_item)
            self.reference_table.setItem(i, 1, reference_point_item)
        self.reference_table.blockSignals(False)

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

    def update_variables(self, configurable_options: ConfigurableOptions):
        if self.vocs is None:
            raise Exception("Vocs is None")

        x_axis_items = [
            self.x_axis_combo.itemText(i) for i in range(self.x_axis_combo.count())
        ]

        y_axis_items = [
            self.y_axis_combo.itemText(i) for i in range(self.y_axis_combo.count())
        ]

        combined_set = set(x_axis_items + y_axis_items)

        if self.vocs.variable_names != list(combined_set):
            logger.debug(
                f"Populating axis combos with variable names: {self.vocs.variable_names}"
            )

            self.x_axis_combo.blockSignals(True)
            self.y_axis_combo.blockSignals(True)

            self.x_axis_combo.clear()
            self.y_axis_combo.clear()

            self.x_axis_combo.addItems(self.vocs.variable_names)
            self.y_axis_combo.addItems(self.vocs.variable_names)

            self.x_axis_combo.setCurrentIndex(configurable_options["variable_1"])
            self.y_axis_combo.setCurrentIndex(configurable_options["variable_2"])

            self.x_axis_combo.blockSignals(False)
            self.y_axis_combo.blockSignals(False)

            self.populate_reference_table()

    def update_vocs(
        self,
        vocs: Optional[VOCS],
    ):
        if vocs is None:
            raise Exception("Vocs in None")

        self.vocs = vocs
        logger.debug(f"vocs: {vocs}")
