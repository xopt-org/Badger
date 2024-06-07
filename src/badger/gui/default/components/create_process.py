from multiprocessing import Event, Pipe, Process, Queue

from PyQt5.QtCore import pyqtSignal, QObject

from badger.core_subprocess import run_routine_subprocess

from epics import CAProcess
import threading

class CreateProcess(QObject):
    """
    This class is for creating processes that will be used to run the optimizations.

    Note:
        The new process will be started, but will be holding until the wait_event is set.
    """

    finished = pyqtSignal()
    subprocess_prepared = pyqtSignal(object)

    def list_active_threads(self):
        threads = threading.enumerate()
        print(f"Number of active threads: {len(threads)}\n")
        print("Active threads:")
        for thread in threads:
            print(f"Thread Name: {thread.name}, Thread ID: {thread.ident}, Is Alive: {thread.is_alive()}")

    def create_subprocess(self) -> None:
        """
        Creates a new process and starts it.
        The process and the arguments passed to the process are then emitted on
        the subprocess_prepared signal.
        """
        self.stop_event = Event()
        self.pause_event = Event()
        self.data_queue = Queue()
        self.evaluate_queue = Pipe()
        self.wait_event = Event()
        print("before")
        self.list_active_threads()
        print("after")
        new_process = CAProcess(
            target=run_routine_subprocess,
            args=(
                self.data_queue,
                self.evaluate_queue,
                self.stop_event,
                self.pause_event,
                self.wait_event,
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
            }
        )
        self.finished.emit()
