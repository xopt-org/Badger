from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QMessageBox,
)
import pandas as pd
from PyQt5.QtWidgets import QGroupBox, QCheckBox, QLabel
from PyQt5.QtCore import Qt
from badger.gui.default.components.data_table import (
    update_table,
    get_table_content_as_dict,
)
from badger.gui.default.components.data_table import (
    data_table,
)
from badger.gui.default.windows.load_data_from_run_dialog import (
    BadgerLoadDataFromRunDialog,
)

LABEL_WIDTH = 96

stylesheet_data = """
    #DataPanel {
        border: 4px solid #4AB640;
        border-radius: 4px;
    }
"""

stylesheet_no_data = """
    #DataPanel {
        border: 4px solid #19232D;
        border-radius: 4px;
    }
"""


class BadgerDataPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        # Set up ui
        self.init_ui()

        # DataFrame to keep track of data in table including metadata
        self.table_data = pd.DataFrame()

        self.selected_routine = None  # Keeps track of VOCS in displayed data
        self.env_vocs = None  # Keeps track of selected VOCS from environment tab

        # boolean indicating whether to show metadata in table
        self.info = False

    def init_ui(self):
        """Initialize interface"""
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(8, 8, 8, 8)

        # Panel for data table
        panel_table = QWidget()
        vbox_table = QVBoxLayout(panel_table)
        vbox_table.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel("Run Data")
        title_label.setStyleSheet(
            """
                font-weight: bold;
                padding: 4px;
        """
        )
        title_label.setAlignment(Qt.AlignCenter)  # Center-align the title
        vbox_table.addWidget(title_label, 0)
        vbox.addWidget(panel_table)

        # Data Table
        self.data_table_widget = QWidget()
        self.data_table_widget.setObjectName("DataPanel")
        hbox_data_table = QHBoxLayout(self.data_table_widget)
        hbox_data_table.setContentsMargins(0, 6, 0, 0)
        self.data_table = data_table()
        self.data_table.set_uneditable()
        self.data_table.setMinimumHeight(200)
        hbox_data_table.addWidget(self.data_table)
        vbox.addWidget(self.data_table_widget)

        # Add label, buttons for loading data and clear table
        load_data_options = QWidget()
        hbox_load_data_options = QHBoxLayout(load_data_options)
        hbox_load_data_options.setContentsMargins(0, 0, 0, 0)

        self.btn_load_data = QPushButton("Add Data")
        self.btn_load_data.clicked.connect(self.load_from_dialog)
        self.btn_load_data.setFixedSize(96, 24)
        self.btn_reset_table = QPushButton("Clear Table")
        self.btn_reset_table.clicked.connect(self.reset_data_table)
        self.btn_reset_table.setFixedSize(96, 24)
        hbox_load_data_options.addWidget(self.btn_load_data)
        hbox_load_data_options.addWidget(self.btn_reset_table)
        hbox_load_data_options.setAlignment(Qt.AlignLeft)
        hbox_load_data_options.addStretch()
        self.info_checkbox = QCheckBox("Display metadata  ")
        self.info_checkbox.stateChanged.connect(self.show_metadata)
        hbox_load_data_options.addWidget(self.info_checkbox)
        vbox.addWidget(load_data_options)

        # Widget for data options
        data_opts_config = QWidget()

        data_vbox = QVBoxLayout(data_opts_config)
        data_vbox.setContentsMargins(0, 0, 0, 0)

        generator_group = QGroupBox("Data Options")
        vbox_generator = QVBoxLayout(generator_group)
        self.run_data_checkbox = QCheckBox("Load displayed data into routine")
        self.run_data_checkbox.stateChanged.connect(self.indicate_add_data_to_routine)
        self.run_data_checkbox.setEnabled(False)
        self.init_points_checkbox = QCheckBox("Skip initial point sampling")
        self.init_points_checkbox.setEnabled(False)

        vbox_generator.addWidget(self.run_data_checkbox)
        vbox_generator.addWidget(self.init_points_checkbox)

        # Group
        vbox.addWidget(data_opts_config)
        vbox.addWidget(generator_group)

    def show_metadata(self):
        self.info = self.info_checkbox.isChecked()
        if self.has_data:
            self.update_table(
                self.data_table, self.table_data, vocs=self.selected_routine.vocs
            )

    def update_vocs(self, vocs):
        self.env_vocs = vocs

    def load_from_dialog(self):
        """
        Verify that variables and objectives have been selected, then open dialog to load data
        """
        vocs = self.env_vocs

        if not vocs.variable_names or not vocs.objective_names:
            dialog = QMessageBox(
                text=str("Select Environment + VOCS before adding data!"),
                parent=self,
            )
            dialog.setIcon(QMessageBox.Information)
            dialog.setStandardButtons(QMessageBox.Ok)
            _ = dialog.exec_()

            return
        else:
            _ = self.get_data_from_dialog()

    def set_routine(self, routine):
        self.selected_routine = routine

    def indicate_add_data_to_routine(self):
        """
        This function indicates visually whether the displayed data will be loaded into the routine,
        by placing a green border around the data table.
        """
        if self.run_data_checkbox.isChecked():
            self.data_table_widget.setStyleSheet(stylesheet_data)
            self.init_points_checkbox.setEnabled(True)
        else:
            self.data_table_widget.setStyleSheet(stylesheet_no_data)
            self.init_points_checkbox.setChecked(False)
            self.init_points_checkbox.setEnabled(False)

    @property
    def use_data(self) -> bool:
        """
        True if run_data_checkbox is checked, and there is data to load.
        Otherwise False.
        """
        if self.has_data and self.run_data_checkbox.isChecked():
            return True
        else:
            self.run_data_checkbox.setChecked(False)
            return False

    @property
    def init_points(self) -> bool:
        # Apologies for double negative, should probably be called skip_init_points_checkbox
        return not self.init_points_checkbox.isChecked()

    @property
    def has_data(self) -> bool:
        table_as_dict = get_table_content_as_dict(self.data_table)
        return bool(table_as_dict)

    def get_data_from_dialog(self):
        """
        Opens a dialog window for loading data into generator.
        """
        dlg = BadgerLoadDataFromRunDialog(
            parent=self,
            data_table=self.data_table,
            on_set=self.load_data_from_dialog,
        )
        self.tc_dialog = dlg
        try:
            dlg.exec()
        finally:
            self.tc_dialog = None

    def add_live_data(self, data):
        """
        Add datapoint from optimization run. This function expects a DataFrame as its argument, and concatenates any existing data with
        the new dataframe, and updates the table.

        Arguments:
            data (DataFrame): dataframe containing new data to be added
        """

        if not self.selected_routine:
            print("no routine selected")
            return

        # reorder data columns to display on table
        vocs = self.selected_routine.vocs
        all_data = pd.concat([self.table_data, data], ignore_index=True)

        self.update_table(self.data_table, all_data, vocs)

    def update_table(self, table, data=None, vocs=None) -> None:
        """Makes sure column order remains consistent and self.table_data stays updated
        to match displayed table. Call data_table's update_table method to update the table"""
        data = self._reorder_cols(data)
        self.table_data = data
        update_table(table, data, vocs, info=self.info)

    def get_data(self):
        return self.table_data

    def get_data_as_dict(self) -> dict:
        data = get_table_content_as_dict(self.data_table)
        if not self.info:
            data = self.filter_metadata(data)

        return data

    @property
    def routine(self):
        return self.selected_routine

    def filter_metadata(self, data: dict) -> dict:
        """
        Remove metadata columns from data dictionary
        """
        data_copy = data.copy()

        metadata_cols = ["xopt_runtime", "xopt_error", "timestamp", "live"]
        cols_to_drop = [col for col in metadata_cols if col in data_copy]
        for key in cols_to_drop:
            del data_copy[key]
        return data_copy

    def load_data_from_dialog(self, routine):
        """
        Load routine data from dialog window. Checks to make sure the data in the selected routine to load
        matches VOCS from the environment + VOCS tab. If they match, update table with data.

        Arguments:
            routine (Xopt Routine) : A routine selected from the load data dialog

        """
        # Data from routine to load
        data = routine.data
        # Create copy of data without metadata columns
        filtered_data = self.filter_metadata(data)
        data_keys = list(filtered_data.keys())

        # VOCS selected in environment tab
        selected_vocs = self.env_vocs.variable_names + self.env_vocs.output_names

        # Raise error if loaded data keys do not match selected vocs
        if set(data_keys) != set(selected_vocs):
            dialog = QMessageBox(
                text=str(
                    "Variables and objectives in data must match currently selected VOCS\n\n"
                    "The following are not included in both selected VOCS and data keys:\n\n"
                    f"{list(set(data_keys) ^ set(selected_vocs))}\n"
                ),
                parent=self,
            )
            dialog.setIcon(QMessageBox.Warning)
            dialog.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            result = dialog.exec_()
            if result == QMessageBox.Cancel:
                return
        else:
            # All keys match, add selected routine data to table
            data["live"] = 0
            combined_data = pd.concat([self.table_data, data], ignore_index=True)
            self.run_data_checkbox.setEnabled(True)

            self.selected_routine = routine
            self.update_table(self.data_table, combined_data, routine.vocs)

    def load_data(self, routine):
        """
        Load data from routine and update table

        Arguments:
            routine (Xopt Routine):
        """
        self.set_routine(routine)
        data = routine.data

        self.run_data_checkbox.setEnabled(True)

        self.update_table(
            self.data_table,
            data,
            routine.vocs,
        )

    def _reorder_cols(self, data):
        """
        Reorder datatable columns for consistency. Order will be objectives,
        constraints, variables, then observables, followed by metadata columns
        such as timestamp, xopt_error, xopt_runtime, and live indicator.
        """

        columns = list(data.columns)
        columns_set = set(columns)
        reordered_cols = []
        vocs = self.selected_routine.vocs

        priority_groups = [
            vocs.objective_names,
            vocs.constraint_names,
            vocs.observable_names,
            vocs.variable_names,
            ["timestamp", "xopt_error", "xopt_runtime", "live"],
        ]

        seen = set()
        for group in priority_groups:
            for col_name in group:
                if col_name in columns_set and col_name not in seen:
                    reordered_cols.append(col_name)
                    seen.add(col_name)

        additional_cols = [col for col in columns if col not in seen]
        reordered_cols.extend(additional_cols)

        if list(data.columns) != reordered_cols:
            data = data[reordered_cols]

        return data

    def reset_data_table(self):
        """Reset table and data"""
        self.data_table.clear()
        self.data_table.setRowCount(0)
        self.data_table.setColumnCount(0)
        self.table_data = pd.DataFrame()
        self.run_data_checkbox.setChecked(False)
        self.run_data_checkbox.setEnabled(False)
