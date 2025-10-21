import os
import traceback
from importlib import resources
from typing import List

from badger.gui.default.components.analysis_extensions import AnalysisExtension
import numpy as np
import pandas as pd
import pyqtgraph as pg
from PyQt5.QtCore import pyqtSignal
from pyqtgraph.Qt import QtGui, QtCore

from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QStyledItemDelegate,
    QVBoxLayout,
    QWidget,
)
from xopt import VOCS

from badger.archive import archive_run, BADGER_ARCHIVE_ROOT

# from ...utils import AURORA_PALETTE, FROST_PALETTE
from badger.logbook import BADGER_LOGBOOK_ROOT, send_to_logbook
from badger.routine import Routine
from badger.tests.utils import get_current_vars
from badger.gui.default.windows.message_dialog import BadgerScrollableMessageBox

from badger.gui.default.components.extensions_palette import ExtensionsPalette
from badger.gui.default.components.routine_runner import BadgerRoutineSubprocess

import logging

logger = logging.getLogger(__name__)

# disable chained assignment warning from pydantic
pd.options.mode.chained_assignment = None  # default='warn'


class BadgerOptMonitor(QWidget):
    sig_pause = pyqtSignal(bool)  # True: pause, False: resume
    sig_stop = pyqtSignal()
    sig_lock = pyqtSignal(bool)  # True: lock GUI, False: unlock GUI
    sig_new_run = pyqtSignal()  # start the new run
    sig_run_started = pyqtSignal()  # run started
    sig_stop_run = pyqtSignal()  # stop the run
    sig_run_name = pyqtSignal(str)  # filename of the new run
    sig_status = pyqtSignal(str)  # status information
    sig_inspect = pyqtSignal(int)  # index of the inspector
    sig_progress = pyqtSignal(pd.DataFrame)  # new evaluated solution
    sig_del = pyqtSignal()
    sig_routine_finished = pyqtSignal()
    sig_lock_action = pyqtSignal()
    sig_toggle_reset = pyqtSignal(bool)
    sig_toggle_run = pyqtSignal(bool)
    sig_toggle_other = pyqtSignal(bool)
    sig_env_ready = pyqtSignal()

    def __init__(self, process_manager=None):
        super().__init__()
        # self.setAttribute(Qt.WA_DeleteOnClose, True)

        # For plot type switching
        self.x_plot_y_axis = 0  # 0: raw, 1: normalized
        self.plot_x_axis = 0  # 0: iteration, 1: time
        self.x_plot_relative = True
        # Routine info
        self.routine = None
        self.routine_filename = None
        self.process_manager = process_manager

        # Curves in the monitor
        self.curves_variable = {}
        self.curves_objective = {}
        self.curves_constraint = {}
        self.curves_sta = {}

        # Run optimization
        self.routine_runner = None
        self.running = False
        # Fix the auto range issue
        self.eval_count = 0
        # Termination condition for the run
        self.termination_condition = None

        self.extensions_palette = ExtensionsPalette(self)
        self.active_extensions: list[AnalysisExtension] = []

        self.testing = False
        self.tc_dialog = None
        self.post_run_actions = []

        self.init_ui()
        self.config_logic()
        self._states = None

    @property
    def vocs(self) -> VOCS:
        return self.routine.vocs

    def states(self, new_states: dict) -> None:
        self._states = new_states

    def init_ui(self):
        # Load all icons
        icon_ref = resources.files(__package__) / "../images/play.png"
        with resources.as_file(icon_ref) as icon_path:
            self.icon_play = QIcon(str(icon_path))
        icon_ref = resources.files(__package__) / "../images/pause.png"
        with resources.as_file(icon_ref) as icon_path:
            self.icon_pause = QIcon(str(icon_path))
        icon_ref = resources.files(__package__) / "../images/stop.png"
        with resources.as_file(icon_ref) as icon_path:
            self.icon_stop = QIcon(str(icon_path))

        # self.main_panel = main_panel = QWidget(self)
        # main_panel.setStyleSheet('background-color: #19232D;')
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 8, 0, 0)

        # Config bar
        config_bar = QWidget()
        hbox_config = QHBoxLayout(config_bar)
        hbox_config.setContentsMargins(0, 0, 0, 0)
        label = QLabel("Evaluation History Plot Type")
        label_x = QLabel("X Axis")
        self.cb_plot_x = cb_plot_x = QComboBox()
        cb_plot_x.setItemDelegate(QStyledItemDelegate())
        cb_plot_x.addItems(["Iteration", "Time"])
        label_y = QLabel("Y Axis (Var)")
        self.cb_plot_y = cb_plot_y = QComboBox()
        cb_plot_y.setItemDelegate(QStyledItemDelegate())
        cb_plot_y.addItems(["Raw", "Normalized"])
        self.check_relative = check_relative = QCheckBox("Relative")
        check_relative.setChecked(True)
        hbox_config.addWidget(label)
        # hbox_config.addSpacing(1)
        hbox_config.addWidget(label_x)
        hbox_config.addWidget(cb_plot_x, 1)
        hbox_config.addWidget(label_y)
        hbox_config.addWidget(cb_plot_y, 1)
        hbox_config.addWidget(check_relative)

        # Set up the monitor
        # Don't set show=True or there will be a blank window flashing once
        self.monitor = monitor = pg.GraphicsLayoutWidget()
        pg.setConfigOptions(antialias=True)
        # monitor.ci.setBorder((50, 50, 100))
        # monitor.resize(1000, 600)

        # create vertical cursor lines
        self.inspector_objective = create_cursor_line()
        self.inspector_constraint = create_cursor_line()
        self.inspector_state = create_cursor_line()
        self.inspector_variable = create_cursor_line()

        # add axes
        self.plot_obj = plot_obj = add_axes(
            monitor, "objectives", "Evaluation History (Y)", self.inspector_objective
        )

        monitor.nextRow()  # leave space for the cons plot
        monitor.nextRow()  # leave space for the stas plot
        monitor.nextRow()

        self.plot_var = plot_var = add_axes(
            monitor,
            "Relative Variable Value",
            "Relative Variable History (X)",
            self.inspector_variable,
        )

        plot_var.setXLink(plot_obj)

        self.colors = ["c", "g", "m", "y", "b", "r", "w"]
        self.symbols = ["o", "t", "t1", "s", "p", "h", "d"]

        vbox.addWidget(config_bar)
        vbox.addWidget(monitor)

    # noinspection PyUnresolvedReferences
    def config_logic(self):
        """
        Configure the logic and connections for various interactive elements in the
        application.

        This method sets up event connections and handlers for different interactive
        elements in the application, such as the inspector lines, buttons,
        and visualizations. It establishes connections between signals and slots to
        enable user interaction and control of the application's functionality.

        Notes
        -----
        - The `config_logic` method is intended to be called once during
        the initialization of the application or a specific class. It sets up various
        event handlers and connections for interactive elements.

        - The signals and slots established in this method determine how the
        application responds to user actions, such as button clicks, inspector line
        drags, and selection changes in visualization controls.

        - Ensure that the necessary attributes and dependencies are properly
        initialized before calling this method.

        """

        # Sync the inspector lines
        self.inspector_objective.sigDragged.connect(self.ins_obj_dragged)
        self.inspector_objective.sigPositionChangeFinished.connect(self.ins_drag_done)
        self.inspector_constraint.sigDragged.connect(self.ins_con_dragged)
        self.inspector_constraint.sigPositionChangeFinished.connect(self.ins_drag_done)
        self.inspector_state.sigDragged.connect(self.ins_sta_dragged)
        self.inspector_state.sigPositionChangeFinished.connect(self.ins_drag_done)
        self.inspector_variable.sigDragged.connect(self.ins_var_dragged)
        self.inspector_variable.sigPositionChangeFinished.connect(self.ins_drag_done)
        self.plot_obj.scene().sigMouseClicked.connect(self.on_mouse_click)
        # sigMouseReleased.connect(self.on_mouse_click)

        # Visualization
        self.cb_plot_x.currentIndexChanged.connect(self.select_x_axis)
        self.cb_plot_y.currentIndexChanged.connect(self.select_x_plot_y_axis)
        self.check_relative.stateChanged.connect(self.toggle_x_plot_y_axis_relative)

    def init_plots(self, routine: Routine = None, run_filename: str = None):
        """
        Initialize and configure the plots and related components in the application.

        This method initializes and configures the plot areas, curves, and inspectors
        used for visualizing data in the application. It also manages the state of
        various UI elements based on the provided routine and run information.

        Parameters
        ----------
        routine : Routine,
            The routine to use for configuring the plots. If
            not provided, the method will use the previously set routine.

        run_filename : str, optional
            The filename of the run, used to determine the state of the application's UI
            elements.

        Returns
        -------
        None

        Notes
        -----
        - The `init_plots` method is typically called during the application's
        initialization or when a new routine is selected. It sets up
        the plots, curves, and inspectors for visualizing data.

        - The method relies on the `self.routine`, `self.vocs`, `self.monitor`,
        `self.colors`, `self.symbols`, and other attributes of the class to configure
        the plots and manage UI elements.

        - The `routine` parameter allows you to provide a specific routine for
        configuring the plots. If not provided, it will use the previously set routine.

        - The `run_filename` parameter is used to determine the state of UI elements,
        such as enabling or disabling certain buttons based on whether the run data
        is available.

        """
        if routine is None:
            # if no routines are specified, clear the current plots
            self.plot_var.clear()
            self.plot_obj.clear()

            # if constraints are active delete them
            try:
                self.monitor.removeItem(self.plot_con)
                self.plot_con.removeItem(self.inspector_constraint)
                del self.plot_con
            except:
                pass

            # if statics exist delete that plot
            try:
                self.monitor.removeItem(self.plot_obs)
                self.plot_obs.removeItem(self.inspector_state)
                del self.plot_obs
            except:
                pass

            # if no routine is loaded set button to disabled
            self.sig_lock_action.emit()

            self.routine = None

            return

        self.routine = routine

        # Retrieve data information
        objective_names = self.vocs.objective_names
        variable_names = self.vocs.variable_names
        constraint_names = self.vocs.constraint_names
        sta_names = self.vocs.observable_names

        # Configure variable plots
        self.curves_variable = self._configure_plot(
            self.plot_var, self.inspector_variable, variable_names
        )

        # Configure objective plots
        self.curves_objective = self._configure_plot(
            self.plot_obj, self.inspector_objective, objective_names
        )

        # Configure constraint plots
        if constraint_names:
            try:
                self.plot_con
            except:
                self.plot_con = plot_con = add_axes(
                    self.monitor,
                    "constraints",
                    "Evaluation History (C)",
                    self.inspector_constraint,
                    row=1,
                    col=0,
                )
                plot_con.setXLink(self.plot_obj)

            self.curves_constraint = self._configure_plot(
                self.plot_con, self.inspector_constraint, constraint_names
            )

        else:
            try:
                self.monitor.removeItem(self.plot_con)
                self.plot_con.removeItem(self.inspector_constraint)
                del self.plot_con
            except:
                pass

        # Configure state plots
        if sta_names:
            try:
                self.plot_obs
            except:
                self.plot_obs = plot_obs = add_axes(
                    self.monitor,
                    "observables",
                    "Evaluation History (S)",
                    self.inspector_state,
                    row=2,
                    col=0,
                )
                plot_obs.setXLink(self.plot_obj)

            self.curves_sta = self._configure_plot(
                self.plot_obs, self.inspector_state, sta_names
            )
        else:
            try:
                self.monitor.removeItem(self.plot_obs)
                self.plot_obs.removeItem(self.inspector_state)
                del self.plot_obs
            except:
                pass

        # Reset inspectors
        self.inspector_objective.setValue(0)
        self.inspector_variable.setValue(0)
        self.inspector_constraint.setValue(0)
        self.inspector_state.setValue(0)

        # Switch run button state
        self.sig_toggle_run.emit(False)

        self.eval_count = 0  # reset the evaluation count
        self.enable_auto_range()

        # Reset button should only be available if it's the current run
        if self.routine_runner and self.routine_runner.run_filename == run_filename:
            self.sig_toggle_reset.emit(False)
        else:
            self.sig_toggle_reset.emit(True)

        if routine.data is None:
            self.sig_toggle_other.emit(True)

            return

        self.update_curves()

        self.sig_toggle_other.emit(False)

    def _configure_plot(self, plot_object, inspector, names):
        plot_object.clear()
        plot_object.addItem(inspector)
        curves = {}
        for i, name in enumerate(names):
            color = self.colors[i % len(self.colors)]
            # symbol = self.symbols[i % len(self.colors)]

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

    def init_routine_runner(self):
        self.reset_routine_runner()

        self.routine_runner = routine_runner = BadgerRoutineSubprocess(
            self.process_manager,
            self.routine,
            self.routine_filename,
            save=True,
            testing=self.testing,
        )

        routine_runner.signals.env_ready.connect(self.env_ready)
        routine_runner.signals.finished.connect(self.routine_finished)
        routine_runner.signals.progress.connect(self.update)
        routine_runner.signals.error.connect(self.on_error)
        routine_runner.signals.info.connect(self.on_info)
        routine_runner.signals.states.connect(self.states)

        self.sig_pause.connect(routine_runner.ctrl_routine)
        self.sig_stop.connect(routine_runner.stop_routine)

    def reset_routine_runner(self):
        if self.routine_runner:
            self.sig_pause.disconnect()
            self.sig_stop.disconnect()
            self.routine_runner = None

    def start(
        self,
        run_data_flag: bool = False,
        init_points_flag: bool = False,
        use_termination_condition: bool = False,
    ):
        self.sig_new_run.emit()
        self.sig_status.emit(f"Running routine {self.routine.name}...")
        if not run_data_flag:
            self.routine.data = None  # reset data if any
        self.init_plots(self.routine)
        self.init_routine_runner()
        if use_termination_condition:
            self.routine_runner.set_termination_condition(self.termination_condition)
        self.running = True  # if a routine runner is working
        self.routine_runner.run(
            run_data_flag=run_data_flag, init_points_flag=init_points_flag
        )
        self.sig_run_started.emit()
        self.sig_lock.emit(True)

    def save_termination_condition(self, tc):
        self.termination_condition = tc

    def enable_auto_range(self):
        # Enable autorange
        self.plot_obj.enableAutoRange()
        self.plot_var.enableAutoRange()
        if self.vocs.constraint_names:
            self.plot_con.enableAutoRange()

        if self.vocs.observable_names:
            self.plot_obs.enableAutoRange()

    def open_extensions_palette(self):
        self.extensions_palette.show()

    def extension_window_closed(self, child_window: AnalysisExtension):
        self.active_extensions.remove(child_window)
        self.extensions_palette.update_palette()

    def extract_timestamp(self, data=None):
        if data is None:
            data = self.routine.sorted_data

        return data["timestamp"].to_numpy(copy=True)

    def update(self, results: pd.DataFrame) -> None:
        """Update plots in main window as well as any active extensions and the
        extensions palette

        Parameters
        ----------
        results : pd.DataFrame

        Returns
        -------
        None
        """
        self.update_curves(results)
        self.update_analysis_extensions()
        self.extensions_palette.update_palette()

        # Quick-n-dirty fix to the auto range issue
        self.eval_count += 1
        if self.eval_count < 2:
            self.enable_auto_range()

        self.sig_progress.emit(self.routine.data.tail(1))

        # Check critical condition
        self.check_critical()

    def update_curves(self, results=None):
        use_time_axis = self.plot_x_axis == 1
        normalize_inputs = self.x_plot_y_axis == 1

        if results is not None:
            self.routine.data = results

        if not self.routine or not hasattr(self.routine, "sorted_data"):
            # if no routine or sorted_data is available, return
            return
        data_copy = self.routine.sorted_data

        # Get timestamps
        if use_time_axis:
            ts = self.extract_timestamp(data_copy)
            ts -= ts[0]
        else:
            ts = None

        variable_names = self.vocs.variable_names

        # if normalize x, normalize using vocs
        if normalize_inputs:
            input_data = self.vocs.normalize_inputs(data_copy)
        else:
            input_data = data_copy[variable_names]

        # if plot relative, subtract the first value from the dict
        if self.x_plot_relative:
            input_data[variable_names] = (
                input_data[variable_names] - input_data[variable_names].iloc[0]
            )

        if "live" in data_copy.columns:
            input_data["live"] = data_copy["live"]
        else:
            input_data["live"] = data_copy["live"] = True

        set_data(variable_names, self.curves_variable, input_data, ts)
        set_data(self.vocs.objective_names, self.curves_objective, data_copy, ts)
        set_data(self.vocs.constraint_names, self.curves_constraint, data_copy, ts)
        set_data(self.vocs.observable_names, self.curves_sta, data_copy, ts)

    def check_critical(self) -> None:
        """
        Check if a critical constraint has been violated in the last data point,
        and take appropriate actions if so.

        If there are no critical constraints, the function will return without taking
        any action. If a critical constraint has been violated, it will pause the
        run, open a dialog to inform the user about the violation, and provide
        options to terminate or resume the run.

        Returns
        -------
        None

        Notes
        -----

        The critical constraints are determined by the
        `self.routine.critical_constraint_names` attribute. If no critical
        constraints are defined, this function will have no effect.

        The function emits signals `self.sig_pause` and `self.sig_stop` to handle the
        pause and stop actions.

        """
        # if there are no critical constraints then skip
        if len(self.routine.critical_constraint_names) == 0:
            return

        feas = self.vocs.feasibility_data(self.routine.data.tail(1), prefix="")
        feasible = feas["feasible"].iloc[0].item()
        if feasible:
            return

        # if code reaches this point there is a critical constraint violated
        self.sig_pause.emit(True)
        # self.btn_ctrl.setIcon(self.icon_play)
        # self.btn_ctrl.setToolTip("Resume")
        # self.btn_ctrl._status = "play"

        # Show the list of critical violated constraints
        feas_crit = feas[self.routine.critical_constraint_names]
        violated_crit = feas_crit.columns[~feas_crit.iloc[0]].tolist()
        msg = "\n".join(violated_crit)
        reply = QMessageBox.warning(
            self,
            "Run Paused",
            f"The following critical constraints were violated:\n\n{msg}\n\nTerminate the run?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes,
        )
        if reply == QMessageBox.Yes:
            self.sig_stop.emit()
            self.sig_stop_run.emit()

    def update_analysis_extensions(self) -> None:
        for ele in self.active_extensions:
            try:
                ele.update_window(self.routine)
            except ValueError:
                traceback.print_exc()

    def env_ready(self, init_vars) -> None:
        self.init_vars = init_vars

        self.sig_env_ready.emit()

    def routine_finished(self) -> None:
        self.running = False
        self.sig_routine_finished.emit()

        self.sig_lock.emit(False)

        try:
            # TODO: fill in the states
            # TODO: replace self.testing with with another processes for having a testing mode
            if not self.testing:
                run = archive_run(self.routine, states=self._states)
                self.routine_runner.run_filename = run["filename"]
                env = self.routine.environment
                path = run["path"]
                filename = run["filename"][:-4] + "pickle"

            try:
                env.interface.stop_recording(os.path.join(path, filename))
            except AttributeError:  # recording was not enabled
                pass

            self.sig_run_name.emit(run["filename"])
            self.sig_status.emit(
                f"Archive success: Run data archived to {BADGER_ARCHIVE_ROOT}"
            )
            # if not self.testing:
            #     QMessageBox.information(
            #         self, 'Success!',
            #         f'Archive success: Run data archived to {BADGER_ARCHIVE_ROOT}')

        except Exception as e:
            self.sig_run_name.emit(None)
            self.sig_status.emit(f"Archive failed: {str(e)}")
            # if not self.testing:
            #     QMessageBox.critical(self, 'Archive failed!',
            #                          f'Archive failed: {str(e)}')
        finally:
            for action in self.post_run_actions:
                action()

        # self.reset_routine_runner()

    def destroy_unused_env(self) -> None:
        if not self.running:
            try:
                del self.routine_runner.routine.environment
            except AttributeError:  # env already destroyed
                pass

            try:
                del self.routine.environment
            except AttributeError:  # env already destroyed
                pass

    def on_error(self, error):
        details = error._details if hasattr(error, "_details") else None

        dialog = BadgerScrollableMessageBox(
            title="Error!", text=str(error), parent=self
        )
        dialog.setIcon(QMessageBox.Critical)
        dialog.setDetailedText(details)
        dialog.exec_()

    # Do not show info -- too distracting
    def on_info(self, msg):
        pass

    def logbook(self):
        try:
            send_to_logbook(self.routine, self.monitor)
        except Exception as e:
            self.sig_status.emit(f"Log failed: {str(e)}")
            # QMessageBox.critical(self, 'Log failed!', str(e))

            return

        self.sig_status.emit(f"Log success: Log saved to {BADGER_LOGBOOK_ROOT}")
        # QMessageBox.information(
        #     self, 'Success!', f'')

    def ctrl_routine(self, status):
        self.sig_pause.emit(status)

    def ins_obj_dragged(self, ins_obj):
        self.inspector_variable.setValue(ins_obj.value())
        if self.vocs.constraint_names:
            self.inspector_constraint.setValue(ins_obj.value())
        if self.vocs.observable_names:
            self.inspector_state.setValue(ins_obj.value())

    def ins_con_dragged(self, ins_con):
        self.inspector_variable.setValue(ins_con.value())
        self.inspector_objective.setValue(ins_con.value())
        if self.vocs.observable_names:
            self.inspector_state.setValue(ins_con.value())

    def ins_sta_dragged(self, ins_sta):
        self.inspector_variable.setValue(ins_sta.value())
        self.inspector_objective.setValue(ins_sta.value())
        if self.vocs.constraint_names:
            self.inspector_constraint.setValue(ins_sta.value())

    def ins_var_dragged(self, ins_var):
        self.inspector_objective.setValue(ins_var.value())
        if self.vocs.constraint_names:
            self.inspector_constraint.setValue(ins_var.value())
        if self.vocs.observable_names:
            self.inspector_state.setValue(ins_var.value())

    def ins_drag_done(self, ins):
        self.sync_ins(ins.value())

    def sync_ins(self, pos):
        if self.plot_x_axis:  # x-axis is time
            value, idx = self.closest_ts(pos)
        else:
            try:
                ts = self.extract_timestamp()
                value = idx = np.clip(np.round(pos), 0, len(ts) - 1)
            except:  # no data
                value = idx = np.round(pos)
        self.inspector_objective.setValue(value)
        if self.vocs and self.vocs.constraint_names:
            self.inspector_constraint.setValue(value)
        if self.vocs and self.vocs.observable_names:
            self.inspector_state.setValue(value)
        self.inspector_variable.setValue(value)

        self.sig_inspect.emit(int(idx))

    def closest_ts(self, t):
        # Get the closest timestamp in data regarding t
        ts = self.extract_timestamp()
        ts -= ts[0]
        idx = np.argmin(np.abs(ts - t))

        return ts[idx], idx

    def reset_env(self):
        reply = QMessageBox.question(
            self,
            "Reset Environment",
            f"Are you sure you want to reset the env vars back to {self.init_vars}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        curr_vars = get_current_vars(self.routine)

        self.routine.environment.set_variables(
            dict(zip(self.vocs.variable_names, self.init_vars))
        )

        self.jump_to_solution(0)
        self.sig_inspect.emit(0)
        # Center around the zero position
        if self.plot_x_axis:  # x-axis is time
            pos, _ = self.closest_ts(self.inspector_objective.value())
        else:
            pos = int(self.inspector_objective.value())
        x_range = self.plot_var.getViewBox().viewRange()[0]
        delta = (x_range[1] - x_range[0]) / 2
        self.plot_var.setXRange(pos - delta, pos + delta, padding=0)

        self.sig_status.emit(
            f"Reset environment: Env vars {curr_vars} -> {self.init_vars}"
        )
        # QMessageBox.information(self, 'Reset Environment',
        #                         f'Env vars {curr_vars} -> {self.init_vars}')

    def jump_to_optimal(self):
        try:
            best_idx, _, _ = self.routine.vocs.select_best(
                self.routine.sorted_data, n=1
            )
            # print(best_idx, _)
            best_idx = int(best_idx[0])

            self.jump_to_solution(best_idx)
            self.sig_inspect.emit(best_idx)
        except NotImplementedError:
            QMessageBox.warning(
                self,
                "Jump to optimum",
                "Jump to optimum is not supported for multi-objective optimization yet",
            )

    def jump_to_solution(self, idx):
        if self.plot_x_axis:  # x-axis is time
            ts = self.extract_timestamp()
            value = ts[idx] - ts[0]
        else:
            value = idx

        self.inspector_objective.setValue(value)
        if self.vocs.constraint_names:
            self.inspector_constraint.setValue(value)
        if self.vocs.observable_names:
            self.inspector_state.setValue(value)
        self.inspector_variable.setValue(value)

    def set_vars(self):
        df = self.routine.sorted_data
        if self.plot_x_axis:  # x-axis is time
            pos, idx = self.closest_ts(self.inspector_objective.value())
        else:
            pos = idx = int(self.inspector_objective.value())
        variable_names = self.vocs.variable_names
        solution = df[variable_names].to_numpy()[idx]
        curr_vars = get_current_vars(self.routine)

        reply = QMessageBox.question(
            self,
            "Apply Solution",
            "Are you sure you want to apply the selected solution:\n"
            + "\n".join(
                f"{variable_names[i]}: {round(curr_vars[i], 3)} -> {round(solution[i], 3)},"
                for i in range(len(variable_names))
            )
            + "\nto "
            + f"{self.routine.environment.name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        curr_vars = get_current_vars(self.routine)
        # Patch the hard limit to the environment
        # TODO: this could lead to unexpected behavior
        # since we patched the class variable directly
        # there ought to be a better way to do this
        if self.routine.vrange_hard_limit:
            self.routine.environment.variables.update(self.routine.vrange_hard_limit)
        self.routine.environment.set_variables(dict(zip(variable_names, solution)))
        # center around the inspector
        x_range = self.plot_var.getViewBox().viewRange()[0]
        delta = (x_range[1] - x_range[0]) / 2
        self.plot_var.setXRange(pos - delta, pos + delta, padding=0)

        updated_vars = get_current_vars(self.routine)
        self.sig_status.emit(
            f"Dial in solution: {[f'{variable_names[i]}: {round(curr_vars[i], 4)} -> {round(updated_vars[i], 4)}' for i in range(len(variable_names))]}"
        )
        # QMessageBox.information(
        #     self, 'Set Environment', f'Env vars have been set to {solution}')

    def select_x_axis(self, i):
        self.plot_x_axis = i

        # Switch the x-axis labels
        if i:
            self.plot_var.setLabel("bottom", "time (s)")
            self.plot_obj.setLabel("bottom", "time (s)")
            if self.vocs.constraint_names:
                self.plot_con.setLabel("bottom", "time (s)")
            if self.vocs.observable_names:
                self.plot_obs.setLabel("bottom", "time (s)")
        else:
            self.plot_var.setLabel("bottom", "iterations")
            self.plot_obj.setLabel("bottom", "iterations")
            if self.vocs.constraint_names:
                self.plot_con.setLabel("bottom", "iterations")
            if self.vocs.observable_names:
                self.plot_obs.setLabel("bottom", "iterations")

        # Update inspector line position
        if i:
            ts = self.extract_timestamp()
            value = ts[int(self.inspector_objective.value())] - ts[0]
        else:
            _, value = self.closest_ts(self.inspector_objective.value())
        self.inspector_objective.setValue(value)
        if self.vocs.constraint_names:
            self.inspector_constraint.setValue(value)
        if self.vocs.observable_names:
            self.inspector_state.setValue(value)
        self.inspector_variable.setValue(value)

        self.update_curves()
        self.enable_auto_range()

    def select_x_plot_y_axis(self, i):
        self.x_plot_y_axis = i
        self.update_curves()

    def toggle_x_plot_y_axis_relative(self):
        self.x_plot_relative = self.check_relative.isChecked()

        # Change axes labels depending on if relative is checked
        if self.x_plot_relative:
            self.plot_var.setLabel("left", "Relative Variable Value")
            self.plot_var.setTitle("Relative Variable History (X)")
        else:
            self.plot_var.setLabel("left", "Variable Value")
            self.plot_var.setTitle("Variable History (X)")

        self.update_curves()

    def on_mouse_click(self, event):
        # https://stackoverflow.com/a/64081483
        coor_obj = self.plot_obj.vb.mapSceneToView(event._scenePos)
        if self.vocs and self.vocs.constraint_names:
            coor_con = self.plot_con.vb.mapSceneToView(event._scenePos)
        if self.vocs and self.vocs.observable_names:
            coor_sta = self.plot_obs.vb.mapSceneToView(event._scenePos)
        coor_var = self.plot_var.vb.mapSceneToView(event._scenePos)

        flag = self.plot_obj.viewRect().contains(
            coor_obj
        ) or self.plot_var.viewRect().contains(coor_var)
        if self.vocs and self.vocs.constraint_names:
            flag = flag or self.plot_con.viewRect().contains(coor_con)
        if self.vocs and self.vocs.observable_names:
            flag = flag or self.plot_obs.viewRect().contains(coor_sta)

        if flag:
            self.sync_ins(coor_obj.x())

    def delete_run(self):
        self.sig_del.emit()

    def stop(self):
        self.sig_stop.emit()
        self.sig_stop_run.emit()

    def register_post_run_action(self, action):
        self.post_run_actions.append(action)


def add_axes(monitor, ylabel, title, cursor_line, **kwargs):
    plot_obj = monitor.addPlot(title=title, **kwargs)
    plot_obj.setLabel("left", ylabel)
    plot_obj.setLabel("bottom", "iterations")
    plot_obj.showGrid(x=True, y=True)
    leg_obj = plot_obj.addLegend()
    leg_obj.setBrush((50, 50, 100, 200))

    plot_obj.addItem(cursor_line)

    return plot_obj


def create_cursor_line():
    return pg.InfiniteLine(
        movable=True,
        angle=90,
        label=None,
        labelOpts={
            "position": 0.1,
            "color": (200, 200, 100),
            "fill": (200, 200, 200, 50),
            "movable": True,
        },
    )


def set_data(names: List[str], curves: dict, data: pd.DataFrame, ts=None):
    # Split data into live and not live
    live_mask = data["live"].astype(bool)
    live_data = data.loc[live_mask]
    not_live_data = data.loc[~live_mask]

    # Add first live point to historical data for continuity
    if len(live_data) > 0:
        row_to_add = live_data.head(1)
        not_live_data = pd.concat([not_live_data, row_to_add], ignore_index=False)

    # Determine x-axis data
    if ts is not None:
        live_x = [ts[i] for i in live_data.index.tolist()]
        hist_x = [ts[i] for i in not_live_data.index.tolist()]
    else:
        live_x = live_data.index.to_numpy(dtype=int)
        hist_x = not_live_data.index.to_numpy(dtype=int)

    # Update curves for each name
    for name in names:
        curves[name].setData(live_x, live_data[name].to_numpy(dtype=np.double))
        curves[name + "_hist"].setData(
            hist_x, not_live_data[name].to_numpy(dtype=np.double)
        )
