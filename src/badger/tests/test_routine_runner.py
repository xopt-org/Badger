import pytest
from badger.gui.default.components.process_manager import processManager  
from badger.gui.default.components.create_process import createProcess
from badger.gui.default.components.routine_runner import BadgerRoutineSubprocess
from PyQt5.QtCore import QTimer
from badger.tests.utils import create_routine
from badger.db import save_routine
from PyQt5.QtCore import QTimer
from PyQt5.QtTest import QSignalSpy
import multiprocessing 


class TestRoutineRunner:
        @pytest.fixture(scope='session')
        def init_multiprocessing(self):
            multiprocessing.set_start_method("fork", force=True)

        @pytest.fixture
        def process_manager(self):
            process_manager = processManager()
            process_builder = createProcess()
            process_builder.subprocess_prepared.connect(process_manager.add_to_queue)
            process_builder.create_subprocess()
            return process_manager

        @pytest.fixture
        def instance(self, process_manager, init_multiprocessing):
            from badger.tests.utils import fix_db_path_issue

            fix_db_path_issue()

            routine = create_routine()
            save_routine(routine)
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
             assert instance.stop_event.is_set() == True 
        
        def test_save_init_vars(self, instance):
            sig_env_ready_spy = QSignalSpy(instance.signals.env_ready)
            instance.save_init_vars() 
            assert len(sig_env_ready_spy) == 1

        def test_after_evaluate(self, instance):
            sig_progress_spy = QSignalSpy(instance.signals.progress)
            instance.after_evaluate(True)
            assert len(sig_progress_spy) == 1

        def test_check_queue(self, instance):
            instance.run()
            instance.stop_routine()
            
            sig_finished_spy = QSignalSpy(instance.signals.finished)

            instance.check_queue() 

            assert len(sig_finished_spy) == 1
            assert not instance.timer.isActive()

            #sig_progress_spy = QSignalSpy(instance.signals.progress)
            #instance.run()
            #nstance.check_queue()
            #instance.stop_routine()
            #assert len(sig_progress_spy) > 0 

        
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
            assert instance.process_with_args is not None 
            instance.stop_routine()

        def test_set_termination_condition(self, instance):
            instance.set_termination_condition(True)
            assert instance.termination_condition == True
        