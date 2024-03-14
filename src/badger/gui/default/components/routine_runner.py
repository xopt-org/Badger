import logging

logger = logging.getLogger(__name__)

import time
from xopt import VOCS
from multiprocessing import Queue, Process, Event
from PyQt5.QtCore import pyqtSignal, QObject, QTimer
from ....core import Routine
from ....errors import BadgerRunTerminatedError
from ....core_subprocess import run_routine_subprocess


class BadgerRoutineSignals(QObject):
    env_ready = pyqtSignal(list)
    finished = pyqtSignal()
    progress = pyqtSignal(object)
    routine_data = pyqtSignal(VOCS)
    error = pyqtSignal(Exception)
    info = pyqtSignal(str)


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
        self.timer.setInterval(100)  
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
        self.routine_process.join(timeout=0.2) 

        if self.routine_process.is_alive():
            self.routine_process.terminate()
            self.routine_process.join()
            
        self.timer.stop()
        self.signals.finished.emit()


    def ctrl_routine(self, pause):
        if pause:
            self.pause_event.set()
        else:
            self.pause_event.clear()
