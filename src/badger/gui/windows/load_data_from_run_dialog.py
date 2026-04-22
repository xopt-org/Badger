from PyQt5.QtWidgets import (
    QDialog,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QLabel,
    QFileDialog,
    QMessageBox,
)
from PyQt5.QtCore import Qt
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from typing import List, Callable
import numpy as np
import pandas as pd
from badger.archive import (
    get_base_run_filename,
    get_runs,
    load_run,
)
from badger.gui.components.navigators import HistoryNavigator
from badger.settings import init_settings
from badger.errors import BadgerRoutineError
from badger.routine import Routine
from xopt.vocs import VOCS

stylesheet_run = """
QPushButton:hover:pressed
{
    background-color: #92D38C;
}
QPushButton:hover
{
    background-color: #6EC566;
}
QPushButton
{
    background-color: #4AB640;
    color: #000000;
}
"""


class BadgerLoadDataFromRunDialog(QDialog):
    """
    Dialog for loading generator data in Badger. Provides a UI for selecting a run,
    previewing its data, and loading the data into the application.
    """

    def __init__(
        self,
        parent: QWidget,
        env_vocs: VOCS = None,
        on_set: Callable[[Routine], None] = None,
    ):
        """
        Initialize the dialog.

        Args:
            parent (QWidget): The parent widget.
            data_table (QTableWidget, optional): The data table to update with loaded run data.

        Attributes:
            data_table (QTableWidget): The data table to update with loaded run data.
            selected_routine (Optional[Routine]): The currently selected routine.
        """
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)

        self.selected_routine = None
        self.env_vocs = env_vocs
        self.on_set = on_set  # function from parent to call when loading data

        self.init_ui()
        self.config_logic()

    def init_ui(self) -> None:
        """
        Initialize the user interface.
        """
        config_singleton = init_settings()
        self.BADGER_ARCHIVE_ROOT = config_singleton.read_value("BADGER_ARCHIVE_ROOT")

        self.setWindowTitle("Load Data from Run")
        self.setMinimumWidth(400)

        vbox = QVBoxLayout(self)

        # Header and labels
        header = QWidget()
        header_hbox = QHBoxLayout(header)
        header_hbox.setContentsMargins(0, 0, 0, 0)

        label = QLabel("Select run to load data into generator:")
        label.setFixedWidth(360)
        plot_label = QLabel("Data Preview:")
        plot_label.setFixedWidth(550)
        # var_table_label = QLabel("Variables:")

        header_hbox.addWidget(label)
        header_hbox.addWidget(plot_label)
        # header_hbox.addWidget(var_table_label)

        content_widget = QWidget()
        hbox_content = QHBoxLayout(content_widget)
        hbox_content.setContentsMargins(0, 0, 0, 0)

        # History run browser
        self.history_browser = HistoryNavigator()
        self.history_browser.setFixedWidth(360)
        runs = get_runs()
        self.history_browser.updateItems(runs)
        self.history_browser.history_tree_widget.itemSelectionChanged.connect(
            self.preview_run
        )
        hbox_content.addWidget(self.history_browser)

        # Data preview
        self.data_preview = self.init_plots()
        self.data_preview.setFixedWidth(550)
        hbox_content.addWidget(self.data_preview)

        # Button set
        button_set = QWidget()
        hbox_set = QHBoxLayout(button_set)
        hbox_set.setContentsMargins(0, 0, 0, 0)
        self.btn_from_file = QPushButton("Open File")
        self.btn_cancel = QPushButton("Cancel")
        self.btn_load = QPushButton("Load")
        self.btn_from_file.setFixedSize(96, 24)
        self.btn_cancel.setFixedSize(96, 24)
        self.btn_load.setFixedSize(96, 24)
        hbox_set.addWidget(self.btn_from_file)
        hbox_set.addStretch()
        hbox_set.addWidget(self.btn_cancel)
        hbox_set.addWidget(self.btn_load)

        vbox.addWidget(header)
        vbox.addWidget(content_widget)
        vbox.addWidget(button_set)

    def preview_run(self, routine: Routine = None) -> None:
        """
        Add data to plot to preview the selected run.
        """
        # load data from selected run
        if routine:
            self.selected_routine = routine
        else:
            self.selected_routine = routine = self.load_data(
                get_base_run_filename(self.history_browser.currentText())
            )

        if routine is None:
            return

        # Configure plots
        curves_objective = self._configure_plot(
            self.plot_obj,
            routine.vocs.output_names,
        )

        if len(routine.vocs.constraint_names) > 0:
            curves_constraint = self._configure_plot(
                self.plot_cons,
                routine.vocs.constraint_names,
            )
            self._set_plot_data(
                routine.vocs.constraint_names, curves_constraint, routine.generator.data
            )
            self.plot_cons.show()
        else:
            self.plot_cons.hide()

        curves_variable = self._configure_plot(
            self.plot_var,
            routine.vocs.variable_names,
        )

        self._set_plot_data(
            routine.vocs.output_names, curves_objective, routine.generator.data
        )
        self._set_plot_data(
            routine.vocs.variable_names, curves_variable, routine.generator.data
        )

    def config_logic(self) -> None:
        self.btn_cancel.clicked.connect(self.cancel_changes)
        self.btn_load.clicked.connect(self.select_run)
        self.btn_from_file.clicked.connect(self.load_from_file)

    def select_run(self) -> None:
        """
        Update the data table with variable and objective data from the selected routine
        """
        # Data from routine to load
        data_keys = list(
            self.selected_routine.vocs.variable_names
            + self.selected_routine.vocs.objective_names
        )

        # Check that variables and objectives match selected VOCS
        if set(data_keys) == set(self.env_vocs):
            self.on_set(self.selected_routine)
            self.close()
        else:
            self.show_vocs_mismatch_dialog(data_keys, self.env_vocs)

    def load_from_file(self) -> None:
        options = QFileDialog.Options()
        options |= QFileDialog.ReadOnly
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Data from File",
            "~",
            "YAML Files (*.yaml *.yml);;All Files (*)",
            options=options,
        )

        if not file_path:
            return

        try:
            routine = load_run(file_path)
            self.preview_run(routine)
        except Exception as e:
            raise BadgerRoutineError(f"{e}")

    def load_data(self, run_filename: str) -> None:
        """
        Load data from the selected run.

        Returns:
            Optional[Routine]: The loaded routine or None if loading fails.
        """
        if not run_filename:
            return
        try:
            routine = load_run(run_filename)
            return routine
        except IndexError:
            return
        except Exception:  # failed to load the run
            return

    def init_plots(self) -> None:
        """
        Initialize the plots for data preview. These are static plots styled to
        match the plots on the main GUI from BadgerOptMonitor
        Note: it might be helpful to have some sort of BadgerPlot class
            to be used within the BadgerOptMonitor, which could
            then be reused here!

        Returns:
            pg.GraphicsLayoutWidget: The widget containing the plots.
        """
        self.colors = ["c", "g", "m", "y", "b", "r", "w"]

        plot_layout = pg.GraphicsLayoutWidget()

        # create objectives plot
        self.plot_obj = plot_layout.addPlot(
            row=0, col=0, title="Evaluation History (Y)"
        )
        self.plot_obj.setLabel("left", "objectives")
        self.plot_obj.setLabel("bottom", "iterations")
        self.plot_obj.showGrid(x=True, y=True)
        leg_obj = self.plot_obj.addLegend()
        leg_obj.setBrush((50, 50, 100, 200))

        # create constraints plot
        self.plot_cons = plot_layout.addPlot(
            row=1, col=0, title="Evaluation History (C)"
        )
        self.plot_cons.setLabel("left", "constraints")
        self.plot_cons.setLabel("bottom", "iterations")
        self.plot_cons.showGrid(x=True, y=True)
        leg_cons = self.plot_cons.addLegend()
        leg_cons.setBrush((50, 50, 100, 200))
        # hide unless there are constraints in routine
        self.plot_cons.hide()

        # create variables plot
        self.plot_var = plot_layout.addPlot(
            row=2, col=0, title="Relative Variable History (X)"
        )
        self.plot_var.setLabel("left", "variables")
        self.plot_var.setLabel("bottom", "iterations")
        self.plot_var.showGrid(x=True, y=True)
        leg_obj = self.plot_var.addLegend()
        leg_obj.setBrush((50, 50, 100, 200))

        return plot_layout

    def _configure_plot(
        self, plot_object: pg.PlotItem, names: List[str]
    ) -> dict[str : pg.PlotCurveItem]:
        """
        Configure the plot with the given data names.
        Adapted from BadgerOptMonitor._configure_plot

        Args:
            plot_object (pg.PlotItem): The plot object to configure.
            names (List[str]): The names of the data series.

        Returns:
            dict: A dictionary mapping data names to plot curves.
        """
        plot_object.clear()
        curves = {}
        for i, name in enumerate(names):
            color = self.colors[i % len(self.colors)]

            # add a dot symbol to the plot to handle cases were there are many nans
            dot_symbol = QtGui.QPainterPath()
            size = 0.075  # size of the dot symbol
            dot_symbol.addEllipse(QtCore.QRectF(-size / 2, -size / 2, size, size))

            pen = pg.mkPen(color, width=3)
            hist_pen = pg.mkPen(color, width=3, style=QtCore.Qt.DashLine)
            color = pen.color()
            color.setAlpha(171)
            hist_pen.setColor(color)
            _curve = plot_object.plot(
                pen=pen,
                symbol=dot_symbol,
                symbolPen=pen,
                name=name,
                symbolBrush=pen.color(),
            )
            _curve_hist = plot_object.plot(
                pen=hist_pen, symbol=dot_symbol, name=None, symbolBrush=pen.color()
            )
            curves[name] = _curve
            curves[name + "_hist"] = _curve_hist

        return curves

    def _set_plot_data(
        self, names: List[str], curves: dict, data: pd.DataFrame
    ) -> None:
        """
        Set data for the plot curves.
        Adapted from BadgerOptMonitor.set_data
        """
        # Split data into live and not live
        if "live" in data.columns:
            live_mask = data["live"].astype(bool)
            live_data = data.loc[live_mask]
            not_live_data = data.loc[~live_mask]
        else:
            # If no 'live' column, consider all data as live
            # An alternative could be to check the timestamp of each datapoint
            # against the creation timestamp of the routine
            live_data = data
            not_live_data = pd.DataFrame()

        # Add first live point to historical data for continuity
        if len(live_data) > 0:
            row_to_add = live_data.head(1)
            not_live_data = pd.concat([not_live_data, row_to_add], ignore_index=False)

        # Determine x-axis data
        live_x = live_data.index.to_numpy(dtype=int)
        hist_x = not_live_data.index.to_numpy(dtype=int)

        # Update curves for each name
        for name in names:
            curves[name].setData(live_x, live_data[name].to_numpy(dtype=np.double))
            curves[name + "_hist"].setData(
                hist_x, not_live_data[name].to_numpy(dtype=np.double)
            )

    def show_vocs_mismatch_dialog(self, list1: List[str], list2: List[str]):
        """
        Display a helpful dialog notifying the user that the data they are trying to load
        does not have the same variables and objectives as they have selected in the GUI.
        list1: list of keys (variables + objectives) in data to be loaded
        list2: list of selected VOCS in main GUI for data to be added to
        """
        dialog = QMessageBox(
            text=str(
                "Variables and objectives in data must match currently selected VOCS\n\n"
                + f"Keys in data to load:\n {list1}\n\n"
                + f"Selected VOCS:\n {list2}"
            ),
            parent=None,
        )
        dialog.setIcon(QMessageBox.Warning)
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.exec_()

    def cancel_changes(self):
        self.close()

    def closeEvent(self, event):
        event.accept()
