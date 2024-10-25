from PyQt5.QtWidgets import QMessageBox

class BadgerError(Exception):
    def __init__(self, message="", detailed_text=""):
        super().__init__(message)
        self.detailed_text = detailed_text
        self.show_message_box()

    def show_message_box(self):
        """
        Method to create and display a popup window with the error message. 
        """
        from badger.gui.default.windows.expandable_message_box import ExpandableMessageBox

        error_message = str(self)
        dialog = ExpandableMessageBox(text=error_message, detailedText=self.detailed_text)
        dialog.setIcon(QMessageBox.Critical)
        dialog.exec_()


class BadgerConfigError(BadgerError):
    pass


class VariableRangeError(BadgerError):
    pass


class BadgerNotImplementedError(BadgerError):
    pass


class BadgerDBError(BadgerError):
    pass


class BadgerEnvVarError(BadgerError):
    pass


class BadgerEnvObsError(BadgerError):
    pass


class BadgerNoInterfaceError(BadgerError):
    def __init__(self, detailed_text=None):
        super().__init__(message="Must provide an interface!", detailed_text=detailed_text)


class BadgerInterfaceChannelError(BadgerError):
    pass


class BadgerInvalidPluginError(BadgerError):
    pass


class BadgerPluginNotFoundError(BadgerError):
    pass


class BadgerInvalidDocsError(BadgerError):
    pass


class BadgerLogbookError(BadgerError):
    pass


class BadgerLoadConfigError(BadgerError):
    pass


class BadgerRoutineError(BadgerError):
    pass


class BadgerRunTerminated(Exception):
    def __init__(self, message="Optimization run has been terminated!"):
        super().__init__(message)
