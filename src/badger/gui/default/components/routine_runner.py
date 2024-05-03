import logging

logger = logging.getLogger(__name__)
 
import time
# import debugpy
import traceback
from xopt import VOCS
from PyQt5.QtCore import pyqtSignal, QObject, QTimer
from badger.routine import Routine
from .process_manager import processManager
from ....errors import BadgerRunTerminatedError
from ....tests.utils import get_current_vars
import torch 

class BadgerRoutineSignals(QObject):
    env_ready = pyqtSignal(list)
    finished = pyqtSignal()
    progress = pyqtSignal(object)
    routine_data = pyqtSignal(VOCS)
    error = pyqtSignal(Exception)
    info = pyqtSignal(str)
    

class BadgerRoutineSubprocess():
    """
    This class takes the users choosen routine and then grabs a suprocess to run the routine using code in core_subprocess.py.
    """

    def __init__(self, process_manager: processManager, routine: Routine=None, save: bool=False, verbose: int=2, use_full_ts: bool=False) -> None:
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
        # print('Created a new thread to run the routine.')

        # Signals should belong to instance rather than class
        # Since there could be multiple runners running in parallel
        self.signals = BadgerRoutineSignals()
        self.process_manager = process_manager
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

    def set_termination_condition(self, termination_condition) -> None:
        """
        setter method for the termination condition.

        Paramerters:
            termination_condition : 
        """
        self.termination_condition = termination_condition

    def run(self) -> None:
        """
        This method starts up the routine. 
        The method grabs a subprocess from self.process_manager queue. 
        Then the method unpauses the process along with passing the selected routine name. 
        """

        self.start_time = time.time()
        self.last_dump_time = None  # reset the timer

        # Patch for converting dtype str to torch object
        try:
            dtype = self.routine.generator.turbo_controller.tkwargs['dtype']
            self.routine.generator.turbo_controller.tkwargs['dtype'] = eval(dtype)
        except AttributeError:
            pass
        except KeyError:
            pass
        except TypeError:
            pass

        try:
                self.save_init_vars()
                self.process_with_args = self.process_manager.remove_from_queue()
                self.routine_process = self.process_with_args["process"]
                self.stop_event = self.process_with_args["stop_event"]
                self.pause_event = self.process_with_args["pause_event"]
                self.data_queue = self.process_with_args["data_queue"]
                self.evaluate_queue = self.process_with_args["evaluate_queue"]
                self.wait_event = self.process_with_args["wait_event"]
                
                arg_dict = {
                    'routine_name': self.routine.name,
                    'evaluate': True,
                    'termination_condition': self.termination_condition, 
                    'start_time': self.start_time}
                
                self.data_queue.put(arg_dict)
                self.wait_event.set()
                self.pause_event.set()
                self.setup_timer()

        except BadgerRunTerminatedError as e:
            self.signals.finished.emit()
            self.signals.info.emit(str(e))
        except Exception as e:
            traceback_info = traceback.format_exc()
            e._details = traceback_info
            self.signals.finished.emit()
            self.signals.error.emit(e)


    def setup_timer(self) -> None:
        """
        This sets up a QTimer to check for updates from the subprocess. 
        The clock checks are every 100 miliseconds.  
        """
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_queue)
        self.timer.setInterval(100)  
        self.timer.start() 
        
    def check_queue(self) -> None:
        """
        This method checks the subprocess for updates in the evaluate_queue. 
        It is called by a QTimer every 100 miliseconds.  
        """
        if not self.evaluate_queue.empty():
            while not self.evaluate_queue.empty():                                                  
                results = self.evaluate_queue.get()
                self.after_evaluate(results)

        if not self.routine_process.is_alive():
            self.timer.stop()
            self.signals.finished.emit()

    def after_evaluate(self, results) -> None:
        """
        This method emits updates sent over from the subprocess running the routine on the evaluate_queue.  
        """
        if self.timer.isActive():
            self.signals.progress.emit(results)
            time.sleep(0.1)

    '''
    def save_init_vars(self) -> None:
        """
        Emits the intital variables in the env_ready signal. 
        """
        var_names = self.routine.vocs.variable_names
        var_dict = self.routine.environment._get_variables(var_names)
        init_vars = list(var_dict.values())
    '''

    def save_init_vars(self) -> None:
        """
        Emits the intital variables in the env_ready signal. 
        """
        init_vars = get_current_vars(self.routine)
        self.signals.env_ready.emit(init_vars)

    def stop_routine(self) -> None:
        """
        This method will attempt to close the subprocess running the routine. 
        If the process does not close withing the timeout time (0.1 seconds) then the method will terminate the process. 
        The method then emits a signal that the process has been stopped. 
        """
        self.stop_event.set()
        self.routine_process.join(timeout=0.1) 

        if self.routine_process.is_alive():
            self.routine_process.terminate()
            self.routine_process.join()

        self.timer.stop()
        self.signals.finished.emit()

    def ctrl_routine(self, pause) -> None:
        """
        This method will pause and unpause the routine. 
        This is accomplished by a multiprocessing Event which when set will pause the subprocess.
        """
        if pause:
            self.pause_event.clear()
        else:
            self.pause_event.set()

