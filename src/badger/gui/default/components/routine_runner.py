import logging

logger = logging.getLogger(__name__)
import time
from multiprocessing import Queue, Process, Event
from pandas import DataFrame
from PyQt5.QtCore import pyqtSignal, QObject, QRunnable, QTimer
from ....core import run_routine, Routine
from ....errors import BadgerRunTerminatedError
from ....core_subprocess import run_routine_subprocess
from xopt import VOCS
from typing import Any

class BadgerRoutineSignals(QObject):
    env_ready = pyqtSignal(list)
    finished = pyqtSignal()
    progress = pyqtSignal(Any)
    routine_data = pyqtSignal(VOCS)
    error = pyqtSignal(Exception)
    info = pyqtSignal(str)


class BadgerRoutineRunner(QRunnable):
    """
        Seperate thread to run routine using code in core.py

    """

    def __init__(self, routine: Routine, save: bool, verbose=2, use_full_ts=False):
        """
        Parameters
        ----------
        routine: Routine
            Defined routine for runner

        save: bool
            Flag to enable saving to database

        verbose: int, default: 2
            Verbostiy level (higher is more output)

        use_full_ts: bool
            If true use full time stamp info when dumping to database
        """
        super().__init__()

        # Signals should belong to instance rather thaself.after_evaluaten class
        # Since there could be multiple runners running in parallel
        self.signals = BadgerRoutineSignals()

        self.routine = routine
        self.run_filename = None
        self.states = None  # system states to be saved at start of a run
        self.save = save
        self.verbose = verbose
        self.use_full_ts = use_full_ts
        self.termination_condition = None  # additional option to control the optimization flow
        self.start_time = None  # track the time cost of the run
        self.last_dump_time = None  # track the time the run data got dumped

        self.is_paused = False
        self.is_killed = False

    def set_termination_condition(self, termination_condition):
        self.termination_condition = termination_condition

    def run(self) -> None:
        self.start_time = time.time()
        self.last_dump_time = None  # reset the timer

        try:
            self.save_init_vars()

            self.routine.data = None  # reset data
            run_routine(
                self.routine,
                active_callback=self.check_run_status,
                generate_callback=self.before_evaluate,
                evaluate_callback=self.after_evaluate,
                states_callback=self.states_ready
            )
        except BadgerRunTerminatedError as e:
            self.signals.finished.emit()
            self.signals.info.emit(str(e))
        except Exception as e:
            print(e)
            self.signals.finished.emit()
            self.signals.error.emit(e)

    def before_evaluate(self, candidates: DataFrame):
        # vars: ndarray
        while self.is_paused:
            time.sleep(0)
            if self.is_killed:
                raise BadgerRunTerminatedError

        if self.is_killed:
            raise BadgerRunTerminatedError

    def after_evaluate(self, data: DataFrame):
        self.signals.progress.emit()

        # Try dump the run data and interface log to the disk
        # dump_period = float(read_value('BADGER_DATA_DUMP_PERIOD'))
        # if (self.last_dump_time is None) or (
        #         ts_float - self.last_dump_time > dump_period):
        #     self.last_dump_time = ts_float
        #     run = archive_run(self.routine, self.states)
        #     try:
        #         path = run['path']
        #         filename = run['filename'][:-4] + 'pickle'
        #         self.env.interface.stop_recording(os.path.join(path, filename))
        #     except:
        #         pass

        # Take a break to let the outside signal change the status
        time.sleep(0.1)

    def check_run_status(self):
        """
        check for termination condition

        - checks for internal triggers (max eval, max time) and external triggers

        """
        # Check if termination condition has been satisfied
        if self.termination_condition:
            tc_config = self.termination_condition
            idx = tc_config['tc_idx']
            if idx == 0:
                max_eval = tc_config['max_eval']
                if len(self.routine.data) >= max_eval:
                    return 2

            elif idx == 1:
                max_time = tc_config['max_time']
                dt = time.time() - self.start_time
                if dt >= max_time:
                    return 2

        # External triggers
        if self.is_killed:
            return 2
        elif self.is_paused:
            return 1
        else:
            return 0  # continue to run

    def save_init_vars(self):
        var_names = self.routine.vocs.variable_names
        var_dict = self.routine.environment._get_variables(var_names)
        init_vars = list(var_dict.values())
        self.signals.env_ready.emit(init_vars)

    def states_ready(self, states):
        self.states = states

    def ctrl_routine(self, pause):
        self.is_paused = pause

    def stop_routine(self):
        self.is_killed = True


class BadgerRoutineSubprocess():
    """
        launches suprocess to run routine using code in core.py
    """

    def __init__(self, routine: Routine, save: bool, verbose=2, use_full_ts=False):
        """
        Parameters
        ----------
        routine: Routine
            Defined routine for runner
        save: bool
            Flag to enable saving to database
        verbose: int, default: 2
            Verbostiy level (higher is more output)
        use_full_ts: bool
            If true use full time stamp info when dumping to database
        """
        super().__init__()

        # Signals should belong to instance rather than class
        # Since there could be multiple runners running in parallel
        self.signals = BadgerRoutineSignals()

        self.routine = routine
        self.run_filename = None
        self.states = None  # system states to be saved at start of a run
        self.save = save
        self.verbose = verbose
        self.use_full_ts = use_full_ts
        self.termination_condition = None  # additional option to control the optimization flow
        self.start_time = None  # track the time cost of the run
        self.last_dump_time = None  # track the time the run data got dumped

        self.data_queue = None
        self.stop_event = None
        self.pause_event = None 
        self.routine_process = None 
        self.is_killed = False

    def set_termination_condition(self, termination_condition):
        self.termination_condition = termination_condition

    def run(self) -> None:
        self.start_time = time.time()
        self.last_dump_time = None  # reset the timer

        try:
                self.save_init_vars()
                self.stop_event = Event()
                self.pause_event = Event()
                self.data_queue = Queue()
                self.routine_queue = Queue()
                self.evaluate_queue = Queue()

                arg_dict = {
                    'routine_name': self.routine.name,
                    'evaluate': True,
                    'termination_condition': self.termination_condition}

                self.routine_process = Process(target=run_routine_subprocess, 
                                               args=(self.data_queue, 
                                                     self.evaluate_queue, 
                                                     self.routine_queue,
                                                     self.stop_event, 
                                                     self.pause_event,))
                self.routine_process.start()

                self.data_queue.put(arg_dict)

                self.setup_timer()
                #self.routine.data = None # reset data

        except BadgerRunTerminatedError as e:
            self.signals.finished.emit()
            self.signals.info.emit(str(e))
        except Exception as e:
            print(e)
            self.signals.finished.emit()
            self.signals.error.emit(e)


    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_queue)
        self.timer.setInterval(200)  
        self.timer.start() 
        
    def check_queue(self):
        if not self.routine_queue.empty():
            data = self.routine_queue.get()
            self.signals.routine_data.emit(data)

        if not self.evaluate_queue.empty():
            results = self.evaluate_queue.get()
            self.after_evaluate(results)

    def after_evaluate(self, results):
        self.signals.progress.emit(results)
        time.sleep(0.1)

    def save_init_vars(self):
        var_names = self.routine.vocs.variable_names
        var_dict = self.routine.environment._get_variables(var_names)
        init_vars = list(var_dict.values())
        self.signals.env_ready.emit(init_vars)

    def stop_routine(self):
        self.stop_event.set()
        self.routine_process.join(timeout=2) # hmm 0.7 seconds 

        if self.routine_process.is_alive():
            print('hard stop')
            self.routine_process.terminate()

        self.timer.stop()
        print('Killed')
        self.is_killed = True

    def ctrl_routine(self, pause):
        if pause:
            self.pause_event.set()
        else:
            self.pause_event.clear()
