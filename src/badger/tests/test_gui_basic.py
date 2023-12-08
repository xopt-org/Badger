import pytest
from PyQt5.QtCore import Qt


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
