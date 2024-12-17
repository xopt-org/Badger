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
from typing import Callable, Optional

from xopt import VOCS

import logging


logger = logging.getLogger(__name__)


class UIComponents:
    def __init__(self, vocs: Optional[VOCS] = None):
        self.vocs = vocs
        self.variable_checkboxes = {}
        self.ref_inputs: list[QTableWidgetItem] = []
        self.reference_table = None  # Will be initialized later

        # Initialize other UI components
        self.update_button = QPushButton("Update")
        self.x_axis_combo = QComboBox()
        self.y_axis_combo = QComboBox()
        self.y_axis_checkbox = QCheckBox("Include Variable 2")
        self.y_axis_checkbox.setChecked(True)  # Set checked by default
        self.acq_func_checkbox = QCheckBox("Show Acquisition Function")
        self.acq_func_checkbox.setChecked(True)  # Set checked by default
        self.show_samples_checkbox = QCheckBox("Show Samples")
        self.show_samples_checkbox.setChecked(True)  # Set checked by default
        self.show_prior_mean_checkbox = QCheckBox("Show Prior Mean")
        self.show_feasibility_checkbox = QCheckBox("Show Feasibility")
        self.n_grid = QSpinBox()
        self.n_grid.setRange(10, 100)
        self.n_grid.setValue(50)  # Default value

        # Initialize layouts
        self.variable_checkboxes_layout = None

    def initialize_variable_checkboxes(
        self, state_changed_callback: Optional[Callable[[], None]] = None
    ):
        logger.debug("Initializing variable checkboxes")
        if not self.vocs:
            return

        self.variable_checkboxes = {}
        self.variable_checkboxes_layout = QVBoxLayout()

        for var in self.vocs.variable_names:
            checkbox = QCheckBox(var)
            checkbox.setChecked(True)  # Select all variables by default
            if state_changed_callback:
                checkbox.stateChanged.connect(state_changed_callback)
            self.variable_checkboxes[var] = checkbox
            self.variable_checkboxes_layout.addWidget(checkbox)

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

    def create_reference_inputs(self):
        group_box = QGroupBox("Reference Points")
        layout = QVBoxLayout()

        self.reference_table = QTableWidget()
        self.reference_table.setColumnCount(2)
        self.reference_table.setHorizontalHeaderLabels(["Variable", "Ref. Point"])
        horizontal_header = self.reference_table.horizontalHeader()
        if horizontal_header is not None:
            horizontal_header.setSectionResizeMode(QHeaderView.Stretch)

        self.ref_inputs = []

        if self.vocs:
            self.populate_reference_table()

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
            default_value = (
                self.vocs.variables[var_name][0] + self.vocs.variables[var_name][1]
            ) / 2
            reference_point_item = QTableWidgetItem(str(default_value))
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

    def update_vocs(
        self,
        vocs: Optional[VOCS],
        state_changed_callback: Optional[Callable[[], None]] = None,
    ):
        self.vocs = vocs
        logger.debug(f"vocs: {vocs}")
        # List all items in the x_axis_combo QComboBox
        x_axis_items = [
            self.x_axis_combo.itemText(i) for i in range(self.x_axis_combo.count())
        ]
        logger.debug(f"x_axis_combo items: {x_axis_items}")

        y_axis_items = [
            self.y_axis_combo.itemText(i) for i in range(self.y_axis_combo.count())
        ]
        logger.debug(f"y_axis_combo items: {y_axis_items}")

        combined_set = set(x_axis_items + y_axis_items)

        if self.vocs is None:
            raise Exception("Vocs in None")

        if self.vocs.variable_names != list(combined_set):
            logger.debug(
                f"Populating axis combos with variable names: {self.vocs.variable_names}"
            )
            self.x_axis_combo.clear()
            self.y_axis_combo.clear()

            self.x_axis_combo.addItems(self.vocs.variable_names)
            self.y_axis_combo.addItems(self.vocs.variable_names)

            # Re-initialize variable checkboxes if needed

            self.initialize_variable_checkboxes(state_changed_callback)
            self.populate_reference_table()