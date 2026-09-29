"""Keeps a pool of pre-spawned subprocesses ready to run optimizations.
When one is consumed by a run, signals that a new one should be created."""

from __future__ import annotations

from dataclasses import dataclass
from multiprocessing import Process, Queue
from multiprocessing.connection import Connection
from multiprocessing.synchronize import Event
from typing import TYPE_CHECKING, Any

from PyQt5.QtCore import QObject, pyqtSignal

if TYPE_CHECKING:
    from badger.gui.components.routine_runner import ArgumentDict


@dataclass
class ProcessWithArgs:
    process: Process
    stop_event: Event
    pause_event: Event
    args_queue: Queue[ArgumentDict]
    data_queue: Queue[dict[str, Any] | tuple[str, str]]
    evaluate_queue: tuple[Connection, Connection]
    wait_event: Event
    dialog_action_queue: Queue[dict[str, str]]


class ProcessManager(QObject):
    """
    The ProcessManager class is for holding an array of live processes
    which can be used by Badger to run optimizations.
    """

    processQueueUpdated = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self.processes_queue: list[ProcessWithArgs] = []

    def add_to_queue(self, process_with_args: ProcessWithArgs) -> None:
        """
        Add to a ProcessWithArgs object containing a process and its corresponding args to the processes_queue.

        Parameters
        ----------
        process_with_args: ProcessWithArgs
        """
        self.processes_queue.append(process_with_args)

    def remove_from_queue(self) -> ProcessWithArgs | None:
        """
        Removes and returns a ProcessWithArgs object from the processes_queue.
        If no ProcessWithArgs objects are in the processes_queue then the method returns None.

        Returns
        -------
        process_with_args: ProcessWithArgs | None
        """
        if self.processes_queue:
            process_with_args = self.processes_queue.pop(0)
            self.processQueueUpdated.emit(self.processes_queue)
            return process_with_args

        return None

    def close_processes(self) -> bool:
        """
        Closes the ProcessWithArgs objects stored in the processes_queue.

        Returns
        -------
        True: bool
        """
        for i in range(len(self.processes_queue)):
            _p = self.processes_queue.pop(0)
            _p.process.terminate()
            _p.process.join()

        return True
