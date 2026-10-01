import multiprocessing
from collections.abc import Generator
from unittest.mock import Mock

import pytest
from PyQt5.QtCore import QTimer
from PyQt5.QtTest import QSignalSpy

from badger.gui.components.process_manager import ProcessManager
from badger.gui.components.routine_runner import BadgerRoutineSubprocess


class TestRoutineRunner:
    @pytest.fixture(scope="session", autouse=True)
    def init_multiprocessing(self) -> None:
        # Use 'spawn' on Windows, 'fork' on Unix-like systems
        method = (
            "spawn"
            if multiprocessing.get_start_method(allow_none=True) != "fork"
            else "fork"
        )
        multiprocessing.set_start_method(method, force=True)

    @pytest.fixture
    def process_manager(self) -> Generator[ProcessManager, None, None]:
        from badger.gui.components.create_process import CreateProcess

        process_manager = ProcessManager()
        process_builder = CreateProcess()
        process_builder.subprocess_prepared.connect(process_manager.add_to_queue)
        process_builder.create_subprocess()

        yield process_manager

        process_manager.close_processes()

    @pytest.fixture
    def instance(self, process_manager: ProcessManager) -> BadgerRoutineSubprocess:
        from badger.archive import save_tmp_run
        from badger.gui.components.routine_runner import (
            BadgerRoutineSubprocess,
        )
        from badger.tests.utils import create_routine

        routine = create_routine()
        _ = save_tmp_run(routine)
        instance = BadgerRoutineSubprocess(process_manager, routine)
        instance.pause_event = multiprocessing.Event()
        return instance

    def test_ctrl_routine(self, instance: BadgerRoutineSubprocess) -> None:
        # Test setting the event
        instance.ctrl_routine(True)
        assert not instance.pause_event.is_set()

        # Test clearing the event
        instance.ctrl_routine(False)
        assert instance.pause_event.is_set()

    def test_stop_routine(self, instance: BadgerRoutineSubprocess) -> None:
        instance.run()
        instance.stop_routine()
        assert instance.stop_event.is_set()

    def test_save_init_vars(self, instance: BadgerRoutineSubprocess) -> None:
        sig_env_ready_spy = QSignalSpy(instance.signals.env_ready)
        instance.save_init_vars()
        assert len(sig_env_ready_spy) == 1

    def test_after_evaluate(self, instance: BadgerRoutineSubprocess) -> None:
        sig_progress_spy = QSignalSpy(instance.signals.progress)
        instance.setup_timer()
        instance.after_evaluate(True)
        assert len(sig_progress_spy) == 1
        instance.timer.stop()

    def test_check_queue(self, instance: BadgerRoutineSubprocess) -> None:
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

    def test_setup_timer(self, instance: BadgerRoutineSubprocess) -> None:
        instance.setup_timer()
        assert isinstance(instance.timer, QTimer)
        assert instance.timer.interval() == 100
        assert instance.timer.isActive()

        instance.timer.stop()

    def test_run(self, instance: BadgerRoutineSubprocess) -> None:
        instance.run()
        instance.ctrl_routine(True)
        assert instance.routine_process.is_alive()
        assert instance.wait_event.is_set()
        instance.stop_routine()

    def test_set_termination_condition(self, instance: BadgerRoutineSubprocess) -> None:
        from badger.types import TerminationConditionConfig

        instance.set_termination_condition(
            TerminationConditionConfig(tc_idx=0, max_eval=2)
        )
        assert instance.termination_condition
