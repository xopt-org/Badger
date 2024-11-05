import logging
import time
import traceback

import pandas as pd
import torch  # noqa: F401. For converting dtype str to torch object.
from PyQt5.QtCore import pyqtSignal, QObject, QTimer

from badger.errors import BadgerRunTerminated
from badger.tests.utils import get_current_vars
from badger.routine import calculate_variable_bounds, calculate_initial_points
from badger.settings import init_settings
from badger.gui.default.components.process_manager import ProcessManager
from badger.routine import Routine
from badger.errors import BadgerError

logger = logging.getLogger(__name__)


class BadgerRoutineSignals(QObject):
    env_ready = pyqtSignal(list)
    finished = pyqtSignal()
    progress = pyqtSignal(object)
    error = pyqtSignal(Exception)
    info = pyqtSignal(str)
    states = pyqtSignal(str)


class BadgerRoutineSubprocess:
    """
    This class takes the users chosen routine and then grabs a subprocess to run the routine
    using code in core_subprocess.py.
    """

    def __init__(
        self,
        process_manager: ProcessManager,
        routine: Routine = None,
        save: bool = False,
        verbose: int = 2,
        use_full_ts: bool = False,
    ) -> None:
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
        self.termination_condition = (
            None  # additional option to control the optimization flow
        )
        self.start_time = None  # track the time cost of the run
        self.last_dump_time = None  # track the time the run data got dumped
        self.data_and_error_queue = None
        self.stop_event = None
        self.pause_event = None
        self.routine_process = None
        self.is_killed = False
        self.interval = 100
        self.config_singleton = init_settings()

    def set_termination_condition(self, termination_condition: dict) -> None:
        """
        Setter method for the termination condition.

        Parameters
        ----------
        termination_condition : dict
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
            dtype = self.routine.generator.turbo_controller.tkwargs["dtype"]
            self.routine.generator.turbo_controller.tkwargs["dtype"] = eval(dtype)
        except AttributeError:
            pass
        except KeyError:
            pass
        except TypeError:
            pass

        self.routine.data = None  # reset data
        # Recalculate the bounds and initial points if asked
        if (
            self.config_singleton.read_value("AUTO_REFRESH")
            and self.routine.relative_to_current
        ):
            variables_updated = calculate_variable_bounds(
                self.routine.vrange_limit_options,
                self.routine.vocs,
                self.routine.environment,
            )

            self.routine.vocs.variables = variables_updated

            init_points = calculate_initial_points(
                self.routine.initial_point_actions,
                self.routine.vocs,
                self.routine.environment,
            )
            try:
                init_points = pd.DataFrame(init_points)
            except IndexError:
                init_points = pd.DataFrame(init_points, index=[0])

            self.routine.initial_points = init_points

        try:
            self.save_init_vars()
            process_with_args = self.process_manager.remove_from_queue()
            self.routine_process = process_with_args["process"]
            self.stop_event = process_with_args["stop_event"]
            self.pause_event = process_with_args["pause_event"]
            self.data_and_error_queue = process_with_args["data_queue"]
            self.evaluate_queue = process_with_args["evaluate_queue"]
            self.wait_event = process_with_args["wait_event"]

            arg_dict = {
                "routine_id": self.routine.id,
                "routine_name": self.routine.name,
                "variable_ranges": self.routine.vocs.variables,
                "initial_points": self.routine.initial_points,
                "evaluate": True,
                "termination_condition": self.termination_condition,
                "start_time": self.start_time,
            }

            self.data_and_error_queue.put(arg_dict)
            self.wait_event.set()
            self.pause_event.set()
            self.setup_timer()
            # self.signals.finished.emit(self.routine.states)

            self.routine.data = None  # reset data
            # Recalculate the bounds and initial points if asked
            if (
                self.config_singleton.read_value("AUTO_REFRESH")
                and self.routine.relative_to_current
            ):
                variables_updated = calculate_variable_bounds(
                    self.routine.vrange_limit_options,
                    self.routine.vocs,
                    self.routine.environment,
                )

                self.routine.vocs.variables = variables_updated

                init_points = calculate_initial_points(
                    self.routine.initial_point_actions,
                    self.routine.vocs,
                    self.routine.environment,
                )
                try:
                    init_points = pd.DataFrame(init_points)
                except IndexError:
                    init_points = pd.DataFrame(init_points, index=[0])

                self.routine.initial_points = init_points

        except BadgerRunTerminated as e:
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
        self.timer.setInterval(self.interval)
        self.timer.start()

    def check_queue(self) -> None:
        """
        This method checks the subprocess for updates in the evaluate_queue.
        It also checks the self.data_and_error_queue to see if an exception was thrown during the routine.
        It is called by a QTimer every 100 miliseconds.
        """
        if self.evaluate_queue[1].poll():
            while self.evaluate_queue[1].poll():
                results = self.evaluate_queue[1].recv()
                self.after_evaluate(results)

        if not self.data_and_error_queue.empty():
            error_title, error_traceback = self.data_and_error_queue.get()
            BadgerError(error_title, error_traceback)

        if not self.routine_process.is_alive():
            self.close()
            self.evaluate_queue[1].close()

    def after_evaluate(self, results: pd.DataFrame) -> None:
        """
        This method emits updates sent over from the subprocess running the routine on the evaluate_queue.

        Parameters
        ----------
        results : DataFrame
        """
        if self.timer.isActive():
            self.signals.progress.emit(results)

    def save_init_vars(self) -> None:
        """
        Emits the intital variables in the env_ready signal.
        """
        init_vars = get_current_vars(self.routine)
        self.signals.env_ready.emit(init_vars)

    def stop_routine(self) -> None:
        """
        This method will attempt to close the subprocess running the routine.
        If the process does not close withing the timeout time (0.1 seconds)
        then the method will terminate the process.
        The method then emits a signal that the process has been stopped.
        """
        self.stop_event.set()
        self.routine_process.join(timeout=0.1)

        if self.routine_process.is_alive():
            self.routine_process.terminate()
            self.routine_process.join()

        self.close()

    def ctrl_routine(self, pause: bool) -> None:
        """
        This method will pause and unpause the routine.
        This is accomplished by a multiprocessing Event which when set will pause the subprocess.

        Parameters
        ----------
        pause : bool
        """
        if pause:
            self.pause_event.clear()
        else:
            self.pause_event.set()

    def close(self) -> None:
        self.timer.stop()
        self.signals.finished.emit()
