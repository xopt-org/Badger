from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QTimer


class TestRoutineRunner:
    def test_routine_runner(self, qtbot):
        from badger.gui.default.components.routine_runner import BadgerRoutineRunner
        from badger.tests.utils import create_routine

        routine = create_routine()

        runner = BadgerRoutineRunner(routine, False)
        runner.set_termination_condition({"tc_idx": 0, "max_eval": 2})

        runner.run()
        assert len(runner.routine.data) == 2

        # TODO: check for signal emit message

    def test_turbo_with_routine_runner(self, qtbot):
        from badger.gui.default.windows.main_window import BadgerMainWindow
        from badger.gui.default.windows.message_dialog import BadgerScrollableMessageBox
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
        params = editor.routine_page.generator_box.edit.toPlainText()
        # Turn on turbo controller
        params = params.replace("turbo_controller: null",
                                "turbo_controller: optimize")
        editor.routine_page.generator_box.edit.setPlainText(params)
        qtbot.keyClicks(editor.routine_page.env_box.cb, "test")
        editor.routine_page.env_box.var_table.cellWidget(0, 0).setChecked(True)
        editor.routine_page.env_box.obj_table.cellWidget(0, 0).setChecked(True)
        qtbot.mouseClick(editor.routine_page.env_box.btn_add_curr,
                         Qt.MouseButton.LeftButton)
        qtbot.mouseClick(editor.btn_save, Qt.MouseButton.LeftButton)

        # Run the routine
        monitor = window.home_page.run_monitor
        monitor.testing = True

        def handle_dialog():
            while monitor.tc_dialog is None:
                QApplication.processEvents()

            # Set max evaluation to 2, then run the optimization
            monitor.tc_dialog.sb_max_eval.setValue(2)
            qtbot.mouseClick(monitor.tc_dialog.btn_run,
                             Qt.MouseButton.LeftButton)

        QTimer.singleShot(0, handle_dialog)

        # Bypass the possible Badger error dialog
        def patched_showEvent(original_showEvent):
            def inner(ins, event):
                original_showEvent(ins, event)  # Call the original showEvent
                QTimer.singleShot(100, ins.accept)  # Close the dialog after 100 ms
            return inner

        BadgerScrollableMessageBox.showEvent = patched_showEvent(
            BadgerScrollableMessageBox.showEvent)

        monitor.run_until_action.trigger()

        # Wait until the run is done
        while monitor.running:
            qtbot.wait(100)

        assert len(monitor.routine.data) == 2
