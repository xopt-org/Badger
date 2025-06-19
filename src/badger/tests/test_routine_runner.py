import multiprocessing

import pytest
from PyQt5.QtCore import QEventLoop, Qt, QTimer
from PyQt5.QtTest import QSignalSpy
from PyQt5.QtWidgets import QApplication
from unittest.mock import Mock


class TestRoutineRunner:
    @pytest.fixture(scope="session")
    def init_multiprocessing(self):
        # Use 'spawn' on Windows, 'fork' on Unix-like systems
        method = (
            "spawn"
            if multiprocessing.get_start_method(allow_none=True) != "fork"
            else "fork"
        )
        multiprocessing.set_start_method(method, force=True)

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
    def instance(self, process_manager, init_multiprocessing):
        from badger.archive import save_tmp_run
        from badger.gui.default.components.routine_runner import (
            BadgerRoutineSubprocess,
        )
        from badger.tests.utils import create_routine

        routine = create_routine()
        _ = save_tmp_run(routine)
        instance = BadgerRoutineSubprocess(process_manager, routine)
        instance.pause_event = multiprocessing.Event()
        return instance

    def test_ctrl_routine(self, instance) -> None:
        # Test setting the event
        instance.ctrl_routine(True)
        assert not instance.pause_event.is_set()

        # Test clearing the event
        instance.ctrl_routine(False)
        assert instance.pause_event.is_set()

    def test_stop_routine(self, instance):
        instance.run()
        instance.stop_routine()
        assert instance.stop_event.is_set()

    def test_save_init_vars(self, instance):
        sig_env_ready_spy = QSignalSpy(instance.signals.env_ready)
        instance.save_init_vars()
        assert len(sig_env_ready_spy) == 1

    def test_after_evaluate(self, instance):
        sig_progress_spy = QSignalSpy(instance.signals.progress)
        instance.setup_timer()
        instance.after_evaluate(True)
        assert len(sig_progress_spy) == 1
        instance.timer.stop()

    def test_check_queue(self, instance):
        sig_finished_spy = QSignalSpy(instance.signals.finished)
        instance.run()
        instance.data_and_error_queue.empty = Mock(return_value=True)
        instance.check_queue()
        instance.stop_routine()
        assert len(sig_finished_spy) == 1
        assert not instance.timer.isActive()

        # sig_progress_spy = QSignalSpy(instance.signals.progress)
        # instance.run()
        # nstance.check_queue()
        # instance.stop_routine()
        # assert len(sig_progress_spy) > 0

    def test_setup_timer(self, instance):
        instance.setup_timer()
        assert isinstance(instance.timer, QTimer)
        assert instance.timer.interval() == 100
        assert instance.timer.isActive()

        instance.timer.stop()

    def test_run(self, instance):
        instance.run()
        instance.ctrl_routine(True)
        assert instance.routine_process.is_alive()
        assert instance.wait_event.is_set()
        instance.stop_routine()

    def test_set_termination_condition(self, instance):
        instance.set_termination_condition(True)
        assert instance.termination_condition

    # TODO: check for signal emit message

    def test_turbo_with_routine_runner(self, qtbot, init_multiprocessing):
        # TODO: make this test more stable
        return

        from badger.gui.acr.windows.main_window import BadgerMainWindow
        from badger.gui.default.windows.message_dialog import (
            BadgerScrollableMessageBox,
        )

        window = BadgerMainWindow()
        # qtbot.addWidget(window)

        loop = QEventLoop()
        QTimer.singleShot(1000, loop.quit)  # 1000 ms pause
        loop.exec_()

        # Create and save a routine
        editor = window.home_page.routine_editor
        # Turn off relative to current
        editor.routine_page.env_box.relative_to_curr.setChecked(False)
        # Config env and vocs
        qtbot.keyClicks(editor.routine_page.env_box.cb, "test")
        editor.routine_page.env_box.var_table.cellWidget(0, 0).setChecked(True)
        editor.routine_page.env_box.obj_table.cellWidget(0, 0).setChecked(True)
        qtbot.mouseClick(
            editor.routine_page.env_box.btn_add_curr, Qt.MouseButton.LeftButton
        )

        # Run the routine
        monitor = window.home_page.run_monitor
        monitor.testing = True

        def handle_dialog():
            while monitor.tc_dialog is None:
                QApplication.processEvents()

            # Set max evaluation to 2, then run the optimization
            monitor.tc_dialog.sb_max_eval.setValue(2)
            qtbot.mouseClick(monitor.tc_dialog.btn_run, Qt.MouseButton.LeftButton)

        QTimer.singleShot(0, handle_dialog)

        # Bypass the possible Badger error dialog
        def patched_showEvent(original_showEvent):
            def inner(ins, event):
                original_showEvent(ins, event)  # Call the original showEvent
                QTimer.singleShot(100, ins.accept)  # Close the dialog after 100 ms

            return inner

        BadgerScrollableMessageBox.showEvent = patched_showEvent(
            BadgerScrollableMessageBox.showEvent
        )

        action_bar = window.home_page.run_action_bar
        action_bar.run_until_action.trigger()
        monitor.routine_runner.data_and_error_queue.empty = Mock(return_value=True)

        # Wait until the run is done
        while monitor.running:
            qtbot.wait(100)

        assert len(monitor.routine.data) == 2

        window.process_manager.close_proccesses()
