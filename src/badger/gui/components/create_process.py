import logging
from multiprocessing import Event, Pipe, Process, Queue
from multiprocessing.connection import Connection
from typing import Any

from PyQt5.QtCore import QObject, pyqtSignal

from badger.core_subprocess import run_routine_subprocess
from badger.log import get_logging_manager
from badger.settings import init_settings

logger = logging.getLogger(__name__)


class CreateProcess(QObject):
    """
    This class is for creating processes that will be used to run the optimizations.

    Note:
        The new process will be started, but will be holding until the wait_event is set.
    """

    finished = pyqtSignal()
    subprocess_prepared = pyqtSignal(object)

    def create_subprocess(self) -> None:
        """
        Creates a new process and starts it.
        The process and the arguments passed to the process are then emitted on
        the subprocess_prepared signal.
        """
        self.stop_event = Event()
        self.pause_event = Event()
        self.data_queue: "Queue[Any]" = Queue()
        self.evaluate_queue: "tuple[Connection, Connection]" = Pipe()
        self.wait_event = Event()
        self.dialog_action_queue: "Queue[Any]" = Queue()

        config_instance = init_settings()._instance
        config_path = config_instance.config_path if config_instance else None

        # Get the logging queue from the centralized manager
        logging_manager = get_logging_manager()
        log_queue = logging_manager.get_queue()
        logger.info("Creating subprocess with centralized logging")

        new_process = Process(
            target=run_routine_subprocess,
            args=(
                self.data_queue,
                self.evaluate_queue,
                self.stop_event,
                self.pause_event,
                self.wait_event,
                self.dialog_action_queue,
                config_path,
                log_queue,
            ),
        )
        new_process.start()
        self.subprocess_prepared.emit(
            {
                "process": new_process,
                "stop_event": self.stop_event,
                "pause_event": self.pause_event,
                "data_queue": self.data_queue,
                "evaluate_queue": self.evaluate_queue,
                "wait_event": self.wait_event,
                "dialog_action_queue": self.dialog_action_queue,
            }
        )
        self.finished.emit()
