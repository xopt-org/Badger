import pytest
from unittest.mock import patch
from PyQt5.QtCore import Qt, QTimer


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

    window.close()  # this action should release the env
    # So we expect an AttributeError here
    with pytest.raises(AttributeError):
        home_page.run_monitor.routine.environment


def test_auto_select_updated_routine(qtbot):
    from badger.gui.default.windows.main_window import BadgerMainWindow
    from badger.tests.utils import fix_db_path_issue

    fix_db_path_issue()

    window = BadgerMainWindow()
    qtbot.addWidget(window)

    # Create and save a routine
    qtbot.mouseClick(window.home_page.btn_new, Qt.MouseButton.LeftButton)
    assert window.home_page.tabs.currentIndex() == 1  # jump to the editor

    editor = window.home_page.routine_editor
    qtbot.keyClicks(editor.routine_page.generator_box.cb,
                    "expected_improvement")
    qtbot.keyClicks(editor.routine_page.env_box.cb, "test")
    editor.routine_page.env_box.var_table.cellWidget(0, 0).setChecked(True)
    editor.routine_page.env_box.obj_table.cellWidget(0, 0).setChecked(True)
    qtbot.mouseClick(editor.btn_save, Qt.MouseButton.LeftButton)
    assert window.home_page.tabs.currentIndex() == 0  # jump back to monitor

    # The routine just created should be activated
    routine_item = window.home_page.routine_list.item(0)
    routine_widget = window.home_page.routine_list.itemWidget(routine_item)
    assert routine_widget.activated

    # Update the routine
    qtbot.keyClicks(editor.routine_page.generator_box.cb, "random")
    qtbot.mouseClick(editor.btn_save, Qt.MouseButton.LeftButton)

    # The updated routine should still be activated
    routine_item = window.home_page.routine_list.item(0)
    routine_widget = window.home_page.routine_list.itemWidget(routine_item)
    assert routine_widget.activated


def test_traceback_during_run(qtbot):
    with patch('badger.core.run_routine') as run_routine_mock:
        run_routine_mock.side_effect = Exception("Test exception")

        from badger.gui.default.windows.main_window import BadgerMainWindow
        from badger.gui.default.windows.message_dialog import BadgerScrollableMessageBox
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

        # Function to replace the original showEvent
        def patched_showEvent(original_showEvent):
            def inner(ins, event):
                original_showEvent(ins, event)  # Call the original showEvent

                assert ins  # make sure the dialog is created
                assert ins.detailedTextWidget.toPlainText()  # make sure it's not empty

                QTimer.singleShot(100, ins.accept)  # Close the dialog after 100 ms
            return inner

        BadgerScrollableMessageBox.showEvent = patched_showEvent(
            BadgerScrollableMessageBox.showEvent)

        home_page.run_monitor.start(True)
        # Wait until the run is done
        while home_page.run_monitor.running:
            qtbot.wait(100)


# TODO: Check the use_low_noise_prior parameter in the routine
# once it's running -- currently use_low_noise_prior is not exposed in the GUI
# so need to check the routine object held by the monitor/runner
def test_default_low_noise_prior_in_bo(qtbot):
    from badger.gui.default.windows.main_window import BadgerMainWindow
    from badger.tests.utils import fix_db_path_issue
    from xopt.generators import all_generator_names
    import yaml

    fix_db_path_issue()

    window = BadgerMainWindow()
    qtbot.addWidget(window)

    # Create and save a routine
    qtbot.mouseClick(window.home_page.btn_new, Qt.MouseButton.LeftButton)
    assert window.home_page.tabs.currentIndex() == 1  # jump to the editor

    editor = window.home_page.routine_editor
    cb_generator = editor.routine_page.generator_box.cb
    algos = [cb_generator.itemText(i) for i in range(cb_generator.count())]
    for algo in algos:
        if algo in all_generator_names['bo']:
            qtbot.keyClicks(editor.routine_page.generator_box.cb, algo)
            params = editor.routine_page.generator_box.edit.toPlainText()
            params_dict = yaml.safe_load(params)

            if 'gp_constructor' in params_dict:
                assert not params_dict['gp_constructor']['use_low_noise_prior']
            else:  # that part of params is hidden so we need to dig deeper
                pass
