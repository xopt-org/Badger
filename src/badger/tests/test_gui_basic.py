import pytest
from unittest.mock import patch
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QSignalSpy


def test_gui_main(qtbot):
    from badger.gui.default.windows.main_window import BadgerMainWindow
    from badger.tests.utils import fix_db_path_issue

    fix_db_path_issue()

    window = BadgerMainWindow()
    qtbot.addWidget(window)

    # Test new routine feature
    qtbot.mouseClick(window.home_page.btn_new, Qt.MouseButton.LeftButton)
    assert window.stacks.currentWidget().tabs.currentIndex() == 1


def test_close_main(qtbot):
    from badger.gui.default.windows.main_window import BadgerMainWindow
    from badger.tests.utils import fix_db_path_issue, create_routine

    fix_db_path_issue()

    window = BadgerMainWindow()
    qtbot.addWidget(window)

    routine = create_routine()
    home_page = window.home_page
    home_page.current_routine = routine
    home_page.run_monitor.testing = True
    home_page.run_monitor.termination_condition = {
        "tc_idx": 0,
        "max_eval": 3,
    }
    home_page.go_run(-1)

    home_page.run_monitor.start(True)
    # Wait until the run is done
    while home_page.run_monitor.running:
        qtbot.wait(100)

    window.close()  # this action show release the env
    # So we expect an AttributeError here
    with pytest.raises(AttributeError):
        routine.environment


def test_del_run(qtbot):
    from badger.gui.default.windows.main_window import BadgerMainWindow
    from badger.tests.utils import fix_db_path_issue, create_routine

    fix_db_path_issue()

    window = BadgerMainWindow()
    qtbot.addWidget(window)

    # Run a routine
    routine = create_routine()
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

    # Variables/objectives monitor should contain some data
    assert len(monitor.plot_var.items) > 0
    assert len(monitor.plot_obj.items) > 0

    # Delete the run and check if the monitors have been cleared
    spy = QSignalSpy(monitor.btn_del.clicked)
    with patch("PyQt5.QtWidgets.QMessageBox.question",
               return_value=QMessageBox.Yes):
        qtbot.mouseClick(monitor.btn_del, Qt.MouseButton.LeftButton)
    assert len(spy) == 1

    # Wait for 1s
    qtbot.wait(1000)

    # Should have no constraints/observables monitor
    with pytest.raises(AttributeError):
        _ = monitor.plot_con
    with pytest.raises(AttributeError):
        _ = monitor.plot_obs
    # Variables/objectives monitor should be cleared
    assert len(monitor.plot_var.items) == 0
    assert len(monitor.plot_obj.items) == 0
