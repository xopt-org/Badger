import sys
import traceback

from PyQt5.QtWidgets import QMessageBox


class BadgerError(Exception):
    def __init__(self, message: str = "", detailed_text: str | None = None) -> None:
        if detailed_text is None:
            detailed_text = self.capture_traceback_or_stack()

        super().__init__(message)
        self.detailed_text = detailed_text
        self.show_message_box()

    def show_message_box(self) -> None:
        """
        Method to create and display a popup window with the error message.
        """
        from badger.gui.windows.expandable_message_box import (
            ExpandableMessageBox,
        )

        error_message = str(self)
        dialog = ExpandableMessageBox(
            text=error_message, detailedText=self.detailed_text
        )
        dialog.setIcon(QMessageBox.Critical)
        dialog.exec_()

    def capture_traceback_or_stack(self) -> str:
        """
        Captures the current traceback if an exception is active, otherwise captures the call stack.
        """
        exc_type, exc_value, exc_traceback = sys.exc_info()
        if exc_traceback:
            return "".join(
                traceback.format_exception(exc_type, exc_value, exc_traceback)
            )
        else:
            return "".join(traceback.format_stack())


class BadgerConfigError(Exception):
    pass


class VariableRangeError(Exception):
    pass


class BadgerNotImplementedError(Exception):
    pass


class BadgerDBError(Exception):
    pass


class BadgerEnvInstantiationError(Exception):
    pass


class BadgerEnvNotFoundError(Exception):
    pass


class BadgerEnvVarError(Exception):
    pass


class BadgerEnvObsError(Exception):
    pass


class BadgerNoInterfaceError(Exception):
    def __init__(self, message: str = "Must provide an interface!") -> None:
        super().__init__(message)


class BadgerInterfaceChannelError(Exception):
    pass


class BadgerInvalidPluginError(Exception):
    pass


class BadgerPluginNotFoundError(Exception):
    pass


class BadgerInvalidDocsError(Exception):
    pass


class BadgerLogbookError(Exception):
    pass


class BadgerLoadConfigError(Exception):
    def __init__(self, message: str = "Config Error!") -> None:
        super().__init__(message)


class BadgerRoutineError(Exception):
    pass


class BadgerRunTerminated(Exception):
    def __init__(self, message: str = "Optimization run has been terminated!") -> None:
        super().__init__(message)


# Constants for measurement-error retry option feature.
# Used in communication between routine runner and subprocess.
MEASUREMENT_ERROR_TYPE = "measurement_error"
MEASUREMENT_ACTION_TYPE = "measurement_action"
MEASUREMENT_ACTION_RETRY = "retry"
MEASUREMENT_ACTION_ABORT = "abort"
