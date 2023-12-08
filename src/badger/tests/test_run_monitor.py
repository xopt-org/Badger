import time
from unittest.mock import patch

import numpy as np

from PyQt5.QtCore import QPointF, Qt, QTimer
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtTest import QSignalSpy, QTest
from PyQt5.QtWidgets import QMessageBox, QApplication


def create_test_run_monitor(add_data=True):
    from badger.gui.default.components.run_monitor import BadgerOptMonitor
    from badger.tests.utils import create_routine, fix_db_path_issue

    fix_db_path_issue()

    monitor = BadgerOptMonitor()
    monitor.testing = True

    routine = create_routine()
    if add_data:
        routine.random_evaluate(10)
    monitor.init_plots(routine)

    if add_data:
        assert len(routine.data) == 10

    return monitor


def test_run_monitor(qtbot):
    from badger.gui.default.components.run_monitor import BadgerOptMonitor
    from badger.tests.utils import create_routine, fix_db_path_issue

    fix_db_path_issue()

    monitor = BadgerOptMonitor()
    monitor.testing = True
    qtbot.addWidget(monitor)

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


def test_routine_identity(qtbot):
    from badger.gui.default.components.run_monitor import BadgerOptMonitor
    from badger.tests.utils import create_routine, fix_db_path_issue

    fix_db_path_issue()

    monitor = BadgerOptMonitor()
    qtbot.addWidget(monitor)

    routine = create_routine()

    # Feed in the sample routine
    monitor.routine = routine
    monitor.init_routine_runner()

    assert monitor.routine_runner.routine == monitor.routine


def test_plotting(qtbot):
    monitor = create_test_run_monitor()
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


def test_click_graph(qtbot, mocker):
    monitor = create_test_run_monitor()
    sig_inspect_spy = QSignalSpy(monitor.sig_inspect)
    monitor.plot_x_axis = True

    mock_event = mocker.MagicMock(spec=QMouseEvent)
    mock_event._scenePos = QPointF(350, 240)

    orginal_value = monitor.inspector_variable.value()
    monitor.on_mouse_click(mock_event)
    new_variable_value = monitor.inspector_variable.value()

    assert new_variable_value != orginal_value
    assert len(sig_inspect_spy) == 1

    # TODO: make asserts for other changes when the graph is clicked on by the user.


def test_x_axis_specification(qtbot, mocker):
    # check iteration/time drop down menu
    monitor = create_test_run_monitor()

    # read time stamp
    time_value = monitor.inspector_variable.value()

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


def test_y_axis_specification(qtbot):
    monitor = create_test_run_monitor(add_data=False)
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


def test_pause_play(qtbot):
    monitor = create_test_run_monitor(add_data=False)

    monitor.termination_condition = {
        "tc_idx": 0,
        "max_eval": 10,
    }
    spy = QSignalSpy(monitor.sig_pause)

    monitor.start(True)
    qtbot.wait(500)

    qtbot.mouseClick(monitor.btn_ctrl, Qt.MouseButton.LeftButton)
    assert len(spy) == 1

    qtbot.wait(500)

    qtbot.mouseClick(monitor.btn_ctrl, Qt.MouseButton.LeftButton)
    assert len(spy) == 2

    while monitor.running:
        qtbot.wait(100)


def test_jump_to_optimum(qtbot):
    monitor = create_test_run_monitor()
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


def test_reset_environment(qtbot):
    from badger.tests.utils import get_current_vars, get_vars_in_row

    # check if reset button click signal is trigged and if state is same as original state after click
    monitor = create_test_run_monitor(add_data=False)
    init_vars = get_current_vars(monitor.routine)

    monitor.termination_condition = {
        "tc_idx": 0,
        "max_eval": 10,
    }
    monitor.start(True)

    # Wait until the run is done
    while monitor.running:
        qtbot.wait(100)

    assert len(monitor.routine.data) == 10

    # Check if current env vars matches the last solution in data
    last_vars = get_vars_in_row(monitor.routine, idx=-1)
    curr_vars = get_current_vars(monitor.routine)
    assert np.all(curr_vars == last_vars)

    # Reset env and confirm
    spy = QSignalSpy(monitor.btn_reset.clicked)

    with patch("PyQt5.QtWidgets.QMessageBox.question", return_value=QMessageBox.Yes):
        with patch("PyQt5.QtWidgets.QMessageBox.information") as mock_info:
            qtbot.mouseClick(monitor.btn_reset, Qt.MouseButton.LeftButton)
            mock_info.assert_called_once()

    assert len(spy) == 1

    # Check if the env has been reset
    curr_vars = get_current_vars(monitor.routine)
    assert np.all(curr_vars == init_vars)


def test_dial_in_solution(qtbot):
    from badger.tests.utils import get_current_vars, get_vars_in_row

    monitor = create_test_run_monitor()

    # Check if current env vars matches the last solution in data
    last_vars = get_vars_in_row(monitor.routine, idx=-1)
    curr_vars = get_current_vars(monitor.routine)
    assert np.all(curr_vars == last_vars)

    # Dial in the solution at the inspector line (should be the first solution)
    current_x_view_range = monitor.plot_var.getViewBox().viewRange()[0]

    spy = QSignalSpy(monitor.btn_set.clicked)
    with patch("PyQt5.QtWidgets.QMessageBox.question", return_value=QMessageBox.Yes):
        qtbot.mouseClick(monitor.btn_set, Qt.MouseButton.LeftButton)
    assert len(spy) == 1

    new_x_view_range = monitor.plot_var.getViewBox().viewRange()[0]

    assert new_x_view_range != current_x_view_range

    # Test if the solution has been dialed in
    first_vars = get_vars_in_row(monitor.routine, idx=0)
    curr_vars = get_current_vars(monitor.routine)
    assert np.all(curr_vars == first_vars)

    monitor.plot_x_axis = False

    with patch("PyQt5.QtWidgets.QMessageBox.question", return_value=QMessageBox.Yes):
        qtbot.mouseClick(monitor.btn_set, Qt.MouseButton.LeftButton)

    not_time_x_view_range = monitor.plot_var.getViewBox().viewRange()[0]

    assert new_x_view_range != not_time_x_view_range


def test_run_until(qtbot):
    monitor = create_test_run_monitor(add_data=False)

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


def test_add_extensions(qtbot):
    from badger.gui.default.components.analysis_extensions import ParetoFrontViewer
    from badger.gui.default.components.run_monitor import BadgerOptMonitor
    from badger.tests.utils import create_routine

    routine = create_routine()
    routine.vocs.objectives = {"f1": "MINIMIZE", "f2": "MAXIMIZE"}

    # test w/o using qtbot
    monitor = BadgerOptMonitor()
    monitor.routine = routine
    qtbot.addWidget(monitor)

    monitor.open_extensions_palette()
    monitor.extensions_palette.add_pf_viewer()

    assert isinstance(monitor.active_extensions[0], ParetoFrontViewer)

    # TODO: logic has been changed, if ext is not applicable it won't be
    # added to the extensions palette. In order to test we need to feed in
    # a MO run here

    # test opening and closing windows
    # monitor = BadgerOptMonitor()
    # qtbot.addWidget(monitor)

    # qtbot.mouseClick(monitor.btn_open_extensions_palette, Qt.LeftButton)
    # qtbot.mouseClick(monitor.extensions_palette.btn_data_viewer, Qt.LeftButton)
    # assert isinstance(monitor.active_extensions[0], ParetoFrontViewer)
    # assert len(monitor.active_extensions) == 1

    # test closing window -- should remove element from active extensions
    # monitor.active_extensions[0].close()
    # assert len(monitor.active_extensions) == 0
    # assert monitor.extensions_palette.n_active_extensions == 0
