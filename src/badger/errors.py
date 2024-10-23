from badger.gui.default.windows.expandable_message_box import ExpandableMessageBox
from PyQt5.QtWidgets import QMessageBox

class BadgerConfigError(Exception):
    pass


class VariableRangeError(Exception):
    pass


class BadgerNotImplementedError(Exception):
    pass


class BadgerRunTerminatedError(Exception):

    def __init__(self, message="Optimization run has been terminated!"):
        super().__init__(message)


class BadgerDBError(Exception):
    pass


class BadgerEnvVarError(Exception):
    pass


class BadgerEnvObsError(Exception):
    pass


class BadgerNoInterfaceError(Exception):

    def __init__(self, message="Must provide an interface!"):
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
    pass


class BadgerRoutineError(Exception):
    def __init__(self, message="", detailed_text=""):
        super().__init__(message)
        self.detailed_text = detailed_text
        self.show_message_box()

    def show_message_box(self):
        """
        Method to create and display a popup window with the error message. 
        """
        error_message = str(self)
        dialog = ExpandableMessageBox(text=error_message, detailedText=self.detailed_text)
        dialog.setIcon(QMessageBox.Critical)
        dialog.exec_()