from typing import Dict, Optional

from PyQt5.QtCore import pyqtSignal, QObject


class ProcessManager(QObject):
    """
    The ProcessManager class is for holding an array of live processes
    which can be used by Badger to run optimizations.
    """

    processQueueUpdated = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self.processes_queue = []

    def add_to_queue(self, process_with_args: Dict) -> None:
        """
        Add to a dict contaitng a process and it's coresponding args to the processes_queue.

        Parameters
        ----------
        process_with_args: dict
        """
        self.processes_queue.append(process_with_args)

    def remove_from_queue(self) -> Optional[Dict]:
        """
        Removes and returns a process and it's coresponding args to the processes_queue.
        If no process are in the processes_queue then the method returns None.

        Returns
        -------
        process_with_args: dict | None
        """
        if self.processes_queue:
            process_with_args = self.processes_queue.pop(0)
            self.processQueueUpdated.emit(self.processes_queue)
            return process_with_args

        return None

    def close_proccesses(self) -> bool:
        """
        Closes the processes stored in the processes_queue.

        Returns
        -------
        True: bool
        """
        for i in range(0, len(self.processes_queue)):
            process = self.processes_queue.pop(0)
            process["process"].terminate()
            process["process"].join()

        return True
