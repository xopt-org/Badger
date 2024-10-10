import multiprocessing
import time
import warnings
from unittest.mock import patch

import numpy as np
import pytest
from PyQt5.QtCore import QEventLoop, QPointF, Qt, QTimer
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtTest import QSignalSpy, QTest
from PyQt5.QtWidgets import QApplication, QMessageBox


class TestRunMonitor:
    @pytest.fixture(scope="session")
    def init_multiprocessing(self):
        multiprocessing.set_start_method("fork", force=True)

    @pytest.fixture
    def process_manager(self):
        from badger.gui.default.components.create_process import CreateProcess
        from badger.gui.default.components.process_manager import ProcessManager

        process_manager = ProcessManager()
        process_builder = CreateProcess()
        process_builder.subprocess_prepared.connect(process_manager.add_to_queue)
        process_builder.create_subprocess()
        yield process_manager

        process_manager.close_proccesses()

    @pytest.fixture
    def monitor(self, process_manager, init_multiprocessing):
        from badger.db import save_routine
        from badger.gui.default.components.run_monitor import BadgerOptMonitor
        from badger.tests.utils import create_routine, fix_db_path_issue

        fix_db_path_issue()
        routine = create_routine()
        save_routine(routine)
        monitor = BadgerOptMonitor(process_manager)
        monitor.testing = True
        monitor.routine = routine

        return monitor

    def add_data(self, monitor):
        monitor.routine.random_evaluate(10)
        monitor.init_plots(monitor.routine)

        assert len(monitor.routine.data) == 10

    def test_run_monitor(self, process_manager):
        from badger.gui.default.components.run_monitor import BadgerOptMonitor
        from badger.tests.utils import create_routine, fix_db_path_issue

        fix_db_path_issue()

        monitor = BadgerOptMonitor(process_manager)
        monitor.testing = True
        # qtbot.addWidget(monitor)

        routine = create_routine()

        # test initialization - first w/o routine
        monitor.init_plots()
        assert monitor.btn_stop.text() == "Run"

        # test initialization - then w/ routine
        monitor.init_plots(routine)
        assert monitor.btn_stop.text() == "Run"

        # add some data
        monitor.routine.step()
        assert len(monitor.routine.data) == 1

        # test updating plots
        monitor.update_curves()
        assert set(monitor.curves_variable.keys()) == {"x0", "x1", "x2", "x3"}
        assert set(monitor.curves_objective.keys()) == {"f"}
        assert set(monitor.curves_constraint.keys()) == {"c"}

        # set up run monitor and test it
        monitor.init_routine_runner()
        monitor.routine_runner.set_termination_condition({"tc_idx": 0, "max_eval": 2})
        spy = QSignalSpy(monitor.routine_runner.signals.progress)
        assert spy.isValid()
        QTest.mouseClick(monitor.btn_stop, Qt.MouseButton.LeftButton)
        time.sleep(1)
        QTest.mouseClick(monitor.btn_stop, Qt.MouseButton.LeftButton)

    def test_routine_identity(self, qtbot, process_manager, init_multiprocessing):
        from badger.db import save_routine
        from badger.gui.default.components.run_monitor import BadgerOptMonitor
        from badger.tests.utils import create_routine, fix_db_path_issue

        fix_db_path_issue()

        monitor = BadgerOptMonitor(process_manager)
        # qtbot.addWidget(monitor)

        routine = create_routine()
        save_routine(routine)

        # Feed in the sample routine
        monitor.routine = routine
        monitor.init_routine_runner()

        assert monitor.routine_runner.routine == monitor.routine

    def test_plotting(self, qtbot, monitor):
        from badger.db import remove_routine

        self.add_data(monitor)
        monitor.update_curves()

        monitor.plot_x_axis = 1
        monitor.update_curves()

        monitor.plot_x_axis = 0
        monitor.x_plot_relative = 1
        monitor.update_curves()

        monitor.plot_x_axis = 1
        monitor.x_plot_relative = 1
        monitor.x_plot_y_axis = 1
        monitor.update_curves()
        remove_routine(monitor.routine)

    def test_click_graph(self, qtbot, monitor, mocker):
        self.add_data(monitor)
        sig_inspect_spy = QSignalSpy(monitor.sig_inspect)
        monitor.plot_x_axis = True

        mock_event = mocker.MagicMock(spec=QMouseEvent)
        mock_event._scenePos = QPointF(350, 240)

        orginal_value = monitor.inspector_variable.value()
        monitor.on_mouse_click(mock_event)
        new_variable_value = monitor.inspector_variable.value()

        assert new_variable_value != orginal_value
        assert len(sig_inspect_spy) == 1

    def create_test_run_monitor(self, process_manager, add_data=True):
        from badger.gui.default.components.run_monitor import BadgerOptMonitor
        from badger.tests.utils import create_routine, fix_db_path_issue

        fix_db_path_issue()

        monitor = BadgerOptMonitor(process_manager)
        monitor.testing = True

        routine = create_routine()
        if add_data:
            routine.random_evaluate(10)
        monitor.init_plots(routine)

        if add_data:
            assert len(routine.data) == 10

        return monitor

    def test_x_axis_specification(self, qtbot, monitor, mocker):
        # check iteration/time drop down menu
        self.add_data(monitor)

        # set inspector line index 1
        monitor.inspector_variable.setValue(1)

        # Iteration selected
        monitor.cb_plot_x.setCurrentIndex(0)

        # Test label setting
        plot_var_axis = monitor.plot_var.getAxis("bottom")
        assert plot_var_axis.label.toPlainText().strip() == "iterations"

        plot_obj_axis = monitor.plot_obj.getAxis("bottom")
        assert plot_obj_axis.label.toPlainText().strip() == "iterations"

        if monitor.vocs.constraint_names:
            plot_con_axis = monitor.plot_con.getAxis("bottom")
            assert plot_con_axis.label.toPlainText().strip() == "iterations"

        assert isinstance(monitor.inspector_objective.value(), int)
        assert isinstance(monitor.inspector_variable.value(), int)
        if monitor.vocs.constraint_names:
            assert isinstance(monitor.inspector_constraint.value(), int)

        # Time selected
        monitor.cb_plot_x.setCurrentIndex(1)

        # Test label setting
        plot_var_axis_time = monitor.plot_var.getAxis("bottom")
        assert plot_var_axis_time.label.toPlainText().strip() == "time (s)"

        plot_obj_axis_time = monitor.plot_obj.getAxis("bottom")
        assert plot_obj_axis_time.label.toPlainText().strip() == "time (s)"

        if monitor.vocs.constraint_names:
            plot_con_axis_time = monitor.plot_con.getAxis("bottom")
            assert plot_con_axis_time.label.toPlainText().strip() == "time (s)"

        mock_event = mocker.MagicMock(spec=QMouseEvent)
        mock_event._scenePos = QPointF(350, 240)

        monitor.on_mouse_click(mock_event)

        # Check type of value
        assert isinstance(monitor.inspector_objective.value(), float)
        assert isinstance(monitor.inspector_variable.value(), float)
        if monitor.vocs.constraint_names:
            assert isinstance(monitor.inspector_constraint.value(), float)

        # Switch between time and iterations and see if index changes
        current_index = monitor.inspector_variable.value()

        monitor.cb_plot_x.setCurrentIndex(0)
        assert current_index != monitor.inspector_variable.value()

        monitor.cb_plot_x.setCurrentIndex(1)
        assert current_index == monitor.inspector_variable.value()

    def test_y_axis_specification(self, qtbot, monitor):
        monitor.termination_condition = {
            "tc_idx": 0,
            "max_eval": 10,
        }
        monitor.start(True)

        # Wait until the run is done
        while monitor.running:
            qtbot.wait(100)

        select_x_plot_y_axis_spy = QSignalSpy(monitor.cb_plot_y.currentIndexChanged)
        index = monitor.inspector_variable.value()

        monitor.check_relative.setChecked(False)

        # check raw - non relative
        monitor.cb_plot_y.setCurrentIndex(0)
        assert len(select_x_plot_y_axis_spy) == 0  # since 0 is the default value
        raw_value = monitor.curves_variable["x0"].getData()[1][index]
        assert raw_value == 0.5

        # relative
        monitor.check_relative.setChecked(True)

        # check non normalized relative.
        relative_value = monitor.curves_variable["x0"].getData()[1][index]
        assert relative_value == 0.0

        # normalized relative
        monitor.cb_plot_y.setCurrentIndex(1)
        assert len(select_x_plot_y_axis_spy) == 1

        normalized_relative_value = monitor.curves_variable["x0"].getData()[1][index]
        assert normalized_relative_value == 0.0

        # raw normalized
        monitor.check_relative.setChecked(False)

        normalized_raw_value = monitor.curves_variable["x0"].getData()[1][index]
        assert normalized_raw_value == 0.75

    def test_pause_play(self, qtbot, monitor):
        monitor.termination_condition = {
            "tc_idx": 0,
            "max_eval": 10,
        }
        spy = QSignalSpy(monitor.sig_pause)

        monitor.start(True)
        # qtbot.wait(500)

        qtbot.mouseClick(monitor.btn_ctrl, Qt.MouseButton.LeftButton)
        assert len(spy) == 1

        qtbot.wait(500)

        qtbot.mouseClick(monitor.btn_ctrl, Qt.MouseButton.LeftButton)
        assert len(spy) == 2

        while monitor.running:
            qtbot.wait(100)

    def test_jump_to_optimum(self, qtbot, monitor):
        self.add_data(monitor)
        spy = QSignalSpy(monitor.btn_opt.clicked)
        qtbot.mouseClick(monitor.btn_opt, Qt.MouseButton.LeftButton)

        qtbot.wait(500)

        data = monitor.routine.sorted_data

        max_value = data["f"].max()
        optimal_value_idx = monitor.inspector_variable.value()
        optimal_value = monitor.routine.sorted_data["f"][optimal_value_idx]

        # Check if signal is triggered
        assert len(spy) == 1

        # Check if it is going to be the optimal solution
        assert max_value == optimal_value

    def test_reset_environment(self, qtbot, init_multiprocessing):
        from badger.db import save_routine
        from badger.gui.default.windows.main_window import BadgerMainWindow
        from badger.tests.utils import (
            create_routine,
            fix_db_path_issue,
            get_current_vars,
            get_vars_in_row,
        )

        fix_db_path_issue()

        window = BadgerMainWindow()

        loop = QEventLoop()
        QTimer.singleShot(1000, loop.quit)  # 1000 ms pause
        loop.exec_()

        # Run a routine
        routine = create_routine()
        save_routine(routine)
        home_page = window.home_page
        home_page.current_routine = routine
        monitor = home_page.run_monitor
        monitor.testing = True

        # check if reset button click signal is trigged and if state is same as original state after click
        init_vars = get_current_vars(routine)

        monitor.termination_condition = {
            "tc_idx": 0,
            "max_eval": 10,
        }
        home_page.go_run(-1)
        monitor.start(True)

        while monitor.running:
            qtbot.wait(100)

        assert len(monitor.routine.data) == 10

        monitor.inspector_objective.setValue(9)

        with patch(
            "PyQt5.QtWidgets.QMessageBox.question", return_value=QMessageBox.Yes
        ):
            # with patch("PyQt5.QtWidgets.QMessageBox.information") as mock_info:
            qtbot.mouseClick(monitor.btn_set, Qt.MouseButton.LeftButton)
            # mock_info.assert_called_once()

        # Check if current env vars matches the last solution in data
        last_vars = get_vars_in_row(monitor.routine, idx=-1)
        curr_vars = get_current_vars(monitor.routine)

        assert np.all(curr_vars == last_vars)

        # Reset env and confirm
        spy = QSignalSpy(monitor.btn_reset.clicked)

        with patch(
            "PyQt5.QtWidgets.QMessageBox.question", return_value=QMessageBox.Yes
        ):
            # with patch("PyQt5.QtWidgets.QMessageBox.information") as mock_info:
            qtbot.mouseClick(monitor.btn_reset, Qt.MouseButton.LeftButton)
            # mock_info.assert_called_once()

        assert len(spy) == 1

        # Check if the env has been reset
        curr_vars = get_current_vars(monitor.routine)
        assert np.all(curr_vars == init_vars)
        window.process_manager.close_proccesses()

    def test_dial_in_solution(self, qtbot, monitor):
        from badger.tests.utils import get_current_vars, get_vars_in_row

        self.add_data(monitor)

        # Check if current env vars matches the last solution in data
        last_vars = get_vars_in_row(monitor.routine, idx=-1)
        curr_vars = get_current_vars(monitor.routine)
        assert np.all(curr_vars == last_vars)

        # Dial in the third solution
        current_x_view_range = monitor.plot_var.getViewBox().viewRange()[0]

        monitor.inspector_objective.setValue(2)

        spy = QSignalSpy(monitor.btn_set.clicked)
        with patch(
            "PyQt5.QtWidgets.QMessageBox.question", return_value=QMessageBox.Yes
        ):
            qtbot.mouseClick(monitor.btn_set, Qt.MouseButton.LeftButton)
        assert len(spy) == 1

        new_x_view_range = monitor.plot_var.getViewBox().viewRange()[0]

        assert new_x_view_range != current_x_view_range

        # Test if the solution has been dialed in
        third_vars = get_vars_in_row(monitor.routine, idx=2)
        curr_vars = get_current_vars(monitor.routine)
        assert np.all(curr_vars == third_vars)

        # monitor.plot_x_axis = False

        # with patch("PyQt5.QtWidgets.QMessageBox.question", return_value=QMessageBox.Yes):
        #     qtbot.mouseClick(monitor.btn_set, Qt.MouseButton.LeftButton)

        # not_time_x_view_range = monitor.plot_var.getViewBox().viewRange()[0]

        # assert new_x_view_range != not_time_x_view_range

    def test_run_until(self, qtbot, monitor):
        def handle_dialog():
            while monitor.tc_dialog is None:
                QApplication.processEvents()

            # Set max evaluation to 5, then run the optimization
            monitor.tc_dialog.sb_max_eval.setValue(5)
            qtbot.mouseClick(monitor.tc_dialog.btn_run, Qt.MouseButton.LeftButton)

        QTimer.singleShot(0, handle_dialog)
        monitor.run_until_action.trigger()

        # Wait until the run is done
        while monitor.running:
            qtbot.wait(100)

        assert len(monitor.routine.data) == 5

    """
    def test_add_extensions(self, qtbot, process_manager, init_multiprocessing):
        from badger.gui.default.components.analysis_extensions import ParetoFrontViewer
        from badger.gui.default.components.run_monitor import BadgerOptMonitor
        from badger.tests.utils import create_routine

        routine = create_routine()
        save_routine(routine)

        routine.vocs.objectives = {"f1": "MINIMIZE", "f2": "MAXIMIZE"}

        # test w/o using qtbot
        monitor = BadgerOptMonitor(process_manager)
        monitor.routine = routine

        monitor.open_extensions_palette()
        monitor.extensions_palette.add_pf_viewer()

        assert isinstance(monitor.active_extensions[0], ParetoFrontViewer)

        # TODO: logic has been changed, if ext is not applicable it won't be
        # added to the extensions palette. In order to test we need to feed in
        # a MO run here

        # test opening and closing windows
        # monitor = BadgerOptMonitor(process_manager)
        # qtbot.addWidget(monitor)

        # qtbot.mouseClick(monitor.btn_open_extensions_palette, Qt.LeftButton)
        # qtbot.mouseClick(monitor.extensions_palette.btn_data_viewer, Qt.LeftButton)
        # assert isinstance(monitor.active_extensions[0], ParetoFrontViewer)
        # assert len(monitor.active_extensions) == 1

        # test closing window -- should remove element from active extensions
        # monitor.active_extensions[0].close()
        # assert len(monitor.active_extensions) == 0
        # assert monitor.extensions_palette.n_active_extensions == 0
    """

    def test_critical_constraints(self, qtbot, process_manager, init_multiprocessing):
        from badger.db import save_routine
        from badger.gui.default.components.run_monitor import BadgerOptMonitor
        from badger.tests.utils import create_routine_critical, fix_db_path_issue

        fix_db_path_issue()

        monitor = BadgerOptMonitor(process_manager)
        monitor.testing = True

        routine = create_routine_critical()
        save_routine(routine)
        monitor.routine = routine
        monitor.init_plots(routine)

        def handle_dialog():
            while monitor.tc_dialog is None:
                QApplication.processEvents()

            # Set max evaluation to 5, then run the optimization
            monitor.tc_dialog.sb_max_eval.setValue(5)

            qtbot.mouseClick(monitor.tc_dialog.btn_run, Qt.MouseButton.LeftButton)

        QTimer.singleShot(0, handle_dialog)
        monitor.run_until_action.trigger()

        # Check if critical violation alert being triggered
        with patch("PyQt5.QtWidgets.QMessageBox.warning", return_value=QMessageBox.Yes):
            while monitor.running:
                qtbot.wait(100)

        assert len(monitor.routine.data) == 1  # early-termination due to violation

    def test_ucb_user_warning(self, init_multiprocessing):
        from badger.tests.utils import create_routine_constrained_ucb

        with warnings.catch_warnings(record=True) as caught_warnings:
            _ = create_routine_constrained_ucb()

            # Check if the user warning is caught
            assert len(caught_warnings) == 1
            assert isinstance(caught_warnings[0].message, UserWarning)

    # Note: this test will delete all the previous runs
    # you might want to run this test last
    # TODO: work out why monitor.plot_con still exists after the last routine is deleated
    def test_del_last_run(self, qtbot, init_multiprocessing):
        from badger.db import save_routine
        from badger.gui.default.windows.main_window import BadgerMainWindow
        from badger.tests.utils import create_routine, fix_db_path_issue

        fix_db_path_issue()

        window = BadgerMainWindow()
        # qtbot.addWidget(window)

        loop = QEventLoop()
        QTimer.singleShot(1000, loop.quit)  # 1000 ms pause
        loop.exec_()

        # Run a routine
        routine = create_routine()
        save_routine(routine)
        home_page = window.home_page
        home_page.current_routine = routine
        monitor = home_page.run_monitor
        monitor.testing = True
        monitor.termination_condition = {
            "tc_idx": 0,
            "max_eval": 3,
        }
        home_page.go_run(-1)
        monitor.start(True)
        while monitor.running:
            qtbot.wait(100)
            # time.sleep(1)

        # Variables/objectives/constraints monitor should contain some data
        assert len(monitor.plot_var.items) > 0
        assert len(monitor.plot_obj.items) > 0
        assert len(monitor.plot_con.items) > 0

        # Delete all the runs and check if the monitors have been cleared
        with patch(
            "PyQt5.QtWidgets.QMessageBox.question", return_value=QMessageBox.Yes
        ):
            while home_page.cb_history.count():
                QTest.mouseClick(monitor.btn_del, Qt.MouseButton.LeftButton)

        # Should have no constraints/observables monitor
        qtbot.wait(100)
        monitor.init_plots()

        with pytest.raises(AttributeError):
            _ = monitor.plot_con
        with pytest.raises(AttributeError):
            _ = monitor.plot_obs

        # Variables/objectives monitor should be cleared
        assert len(monitor.plot_var.items) == 0
        assert len(monitor.plot_obj.items) == 0
        window.process_manager.close_proccesses()

        # Should have no constraints/observables monitor
        with pytest.raises(AttributeError):
            _ = monitor.plot_con
        with pytest.raises(AttributeError):
            _ = monitor.plot_obs
        # Variables/objectives monitor should be cleared
        assert len(monitor.plot_var.items) == 0
        assert len(monitor.plot_obj.items) == 0


# TODO: Test if logbook entry is created correctly and put into the
# correct location when the logbook button is clicked
def test_send_to_logbook(qtbot):
    pass


# TODO: Test if the overlay is shown/hiden correctly
# when start/stop run button is clicked
def test_run_stop_overlay(qtbot):
    pass
