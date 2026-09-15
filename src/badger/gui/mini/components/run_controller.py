"""Coordinate pause, resume, continue, and restart behavior/signals for optimization runs"""

import logging

from PyQt5.QtCore import QObject, pyqtSignal

logger = logging.getLogger(__name__)


class SmartRunController(QObject):
    sig_pause_ctrl = pyqtSignal(bool)
    sig_stop = pyqtSignal()
    sig_start = pyqtSignal(bool)  # bool: load_displayed_data

    def __init__(self) -> None:
        super().__init__()
        self.last_routine_dict = None
        self._pending_start = False
        self._load_data = False
        self._new_routine_dict = None

        self.restart_override_flag: bool = False

    def smart_run(
        self,
        routine_params_dict: dict,
        is_running: bool,
        is_paused: bool,
        data_compatible: bool,
    ):
        """
        Selects whether to pause, resume, continue, or restart a run.

        Parameters
        ----------
        routine_params_dict : dict
            Current routine parameters from the editor.
        is_running : bool
            Whether an optimization subprocess is active.
        is_paused : bool
            Whether the current optimization is paused.
        data_compatible : bool
            Whether the existing data can be reused with the new routine.
        """
        self._new_routine_dict = routine_params_dict

        # Hitting 'stop' should pause the subprocess at the start of the optimization loop
        if is_running and not is_paused:
            # is_running means subprocess is active, not is_paused indicates optimization loop is active
            logger.info("Pausing active routine")
            self.sig_pause_ctrl.emit(True)
            return

        if self.restart_override_flag:
            # skip logic and restart fresh run without data
            self.restart_override_flag = False  # reset flag to false
        else:
            # Then when the button is pressed again to 'play':
            # If nothing has changed on the GUI, it should just resume
            if (
                self.last_routine_dict is not None
                and routine_params_dict == self.last_routine_dict
            ):
                if is_running:
                    logger.info("Resuming (unpause) routine")
                    self.sig_pause_ctrl.emit(False)
                    return
                else:
                    # routine has ended, need to start again
                    self.start_run(True)
                    return

            # If parameters like variable range or algorithm parameters have changed, it needs to stop,
            # then start a new optimization process with the new generator parameters, and load in the previous data
            # to 'continue' the optimization with new parameters
            if self.last_routine_dict is not None and data_compatible:
                if is_running:
                    self._pending_start = True
                    self._load_data = True
                    logger.info("Pending restart queued with displayed data")
                    self.sig_stop.emit()
                    return
                    # wait for routine_finished signal
                else:
                    # there is a last_routine but no active subprocess. Start a new run
                    self.start_run(True)
                    return

        # If variables, objectives, have changed, it should stop, then start a
        # new optimization with the default number of iterations

        # if running, stop and wait for routine_finished signal
        if is_running:
            self._pending_start = True
            self._load_data = False
            logger.info("Pending restart queued without displayed data")
            self.sig_stop.emit()
            # wait for routine_finished_signal
            return

        # start fresh run
        self.start_run(False)

    def set_restart_override_flag(self):
        """
        This method sets a flag to skip logic and restart a new run without data on
        the next play button press. It is called when selecting a past run from the
        history tree, loading a template, reseting environment variables, or dialing
        in a solution.
        The flag will then be reset to false in self.smart_run().
        """
        self.restart_override_flag = True

    def notify_routine_finished(self):
        """Start a pending run after the current routine finishes."""
        if self._pending_start is False:
            return

        self.start_run(self._load_data)

    def start_run(self, load_displayed_data: bool):
        """Emit the signal to start a run with/withoug displayed data.

        Parameters
        ----------
        load_displayed_data : bool
            Whether the displayed routine data should be loaded into the run.
        """
        logger.info(f"Starting run (load_displayed_data={load_displayed_data})")
        self._pending_start = False  # reset to false
        self.last_routine_dict = self._new_routine_dict
        self.sig_start.emit(load_displayed_data)
