from PyQt5.QtWidgets import (
    QDialog,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QLabel,
    QTableWidget,
)
import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from typing import List
import numpy as np
import pandas as pd
from badger.archive import (
    get_base_run_filename,
    get_runs,
    load_run,
)
from badger.gui.default.components.data_table import (
    update_table,
)
from badger.gui.acr.components.history_navigator import HistoryNavigator

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

    def __init__(self, parent, data_table=None):
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

        self.data_table = data_table
        self.selected_routine = None
        # self.on_set = on_set # function from parent to call when loading data -> check for var compatibility

        self.init_ui()
        self.config_logic()

    def init_ui(self):
        """
        Initialize the user interface.
        """
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
        var_table_label = QLabel("Variables:")

        header_hbox.addWidget(label)
        header_hbox.addWidget(plot_label)
        header_hbox.addWidget(var_table_label)

        content_widget = QWidget()
        hbox_content = QHBoxLayout(content_widget)
        hbox_content.setContentsMargins(0, 0, 0, 0)

        # History run browser
        self.history_browser = HistoryNavigator()
        self.history_browser.setFixedWidth(360)
        runs = get_runs()
        self.history_browser.updateItems(runs)
        self.history_browser.tree_widget.itemSelectionChanged.connect(self.preview_run)
        hbox_content.addWidget(self.history_browser)

        # Data preview
        self.data_preview = self.init_plots()
        self.data_preview.setFixedWidth(550)
        hbox_content.addWidget(self.data_preview)

        # Variable compatibility check -> Not currently used
        self.variables_table = QTableWidget()
        self.variables_table.setColumnCount(3)
        self.variables_table.setHorizontalHeaderLabels(
            ["To Load", "Currently Selected"]
        )
        # hbox_content.addWidget(self.variables_table)

        # Button set
        button_set = QWidget()
        hbox_set = QHBoxLayout(button_set)
        hbox_set.setContentsMargins(0, 0, 0, 0)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_load = QPushButton("Load")
        self.btn_cancel.setFixedSize(96, 24)
        self.btn_load.setFixedSize(96, 24)
        hbox_set.addStretch()
        hbox_set.addWidget(self.btn_cancel)
        hbox_set.addWidget(self.btn_load)

        vbox.addWidget(header)
        vbox.addWidget(content_widget)
        vbox.addWidget(button_set)

    def preview_run(self):
        """
        Add data to plot to preview the selected run.
        """
        # load data from selected run
        self.selected_routine = routine = self.load_data()

        if routine is None:
            return

        # Configure plots
        curves_objective = self._configure_plot(
            self.plot_obj,
            routine.vocs.output_names,
        )

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

    def config_logic(self):
        self.btn_cancel.clicked.connect(self.cancel_changes)
        self.btn_load.clicked.connect(self.select_run)

    def select_run(self):
        """
        Update the data table with variable and objective data from the selected routine
        """
        update_table(
            self.data_table,
            self.selected_routine.generator.data,
            self.selected_routine.vocs,
        )
        self.close()

    def load_data(self):
        """
        Load data from the selected run.

        Returns:
            Optional[Routine]: The loaded routine or None if loading fails.
        """
        run_filename = get_base_run_filename(self.history_browser.currentText())
        if not run_filename:
            return
        try:
            routine = load_run(run_filename)
            return routine
        except IndexError:
            return
        except Exception:  # failed to load the run
            return

    def init_plots(self):
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

        self.plot_var = plot_layout.addPlot(
            row=1, col=0, title="Relative Variable History (Y)"
        )
        self.plot_var.setLabel("left", "variables")
        self.plot_var.setLabel("bottom", "iterations")
        self.plot_var.showGrid(x=True, y=True)
        leg_obj = self.plot_var.addLegend()
        leg_obj.setBrush((50, 50, 100, 200))

        return plot_layout

    def _configure_plot(self, plot_object, names):
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
            _curve = plot_object.plot(
                pen=pen,
                symbol=dot_symbol,
                symbolPen=pen,
                name=name,
                symbolBrush=pen.color(),
            )
            curves[name] = _curve

        return curves

    def _set_plot_data(
        self, names: List[str], curves: dict, data: pd.DataFrame, ts=None
    ):
        """
        Set data for the plot curves.
        Adapted from BadgerOptMonitor.set_data
        """
        for name in names:
            if ts is not None:
                curves[name].setData(ts, data[name].to_numpy(dtype=np.double))
            else:
                curves[name].setData(data[name].to_numpy(dtype=np.double))

    def cancel_changes(self):
        self.close()

    def run(self):
        print("dialog run")
        self.close()

    def closeEvent(self, event):
        event.accept()
