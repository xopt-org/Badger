from importlib import resources
import signal
import sys
import time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont, QIcon
from PyQt5 import QtCore
from qdarkstyle import load_stylesheet, LightPalette, DarkPalette

from badger.settings import init_settings
from badger.gui.default.windows.main_window import BadgerMainWindow

import traceback
from badger.errors import BadgerError
from types import TracebackType
from typing import Type, NoReturn

# Fix the scaling issue on multiple monitors w/ different scaling settings
# if sys.platform == 'win32':
#     ctypes.windll.shcore.SetProcessDpiAwareness(1)

if hasattr(QtCore.Qt, "AA_EnableHighDpiScaling"):
    QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, "AA_UseHighDpiPixmaps"):
    QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

# if hasattr(QtCore.Qt, 'HighDpiScaleFactorRoundingPolicy'):
#     QApplication.setAttribute(
#         QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

TIMER = {"time": None}


def on_exit(*args):
    if TIMER["time"] is None:
        print("Press Ctrl/Cmd + C again within 1s to quit Badger")
        TIMER["time"] = time.time()
        return

    TIMER["time"] = None
    print("Goodbye")
    QApplication.quit()


def on_timeout():
    if TIMER["time"] is None:
        return

    now = time.time()
    if (now - TIMER["time"]) > 1:
        TIMER["time"] = None
        print("Timeout, resume the operation...")


def error_handler(
    etype: Type[BaseException], value: BaseException, tb: TracebackType
) -> NoReturn:
    """
    Custom exception handler that formats uncaught exceptions and raises a BadgerError.

    Parameters
    ----------
    etype : Type[BaseException]
        The class of the exception that was raised.
    value : BaseException
        The exception instance.
    tb : TracebackType
        The traceback object associated with the exception.

    Raises
    ------
    BadgerError
        An exception that includes the error title and detailed traceback.
    """
    error_msg = "".join(traceback.format_exception(etype, value, tb))
    error_title = f"{etype.__name__}: {value}"
    raise BadgerError(error_title, error_msg)


def launch_gui():
    sys.excepthook = error_handler
    app = QApplication(sys.argv)
    config_singleton = init_settings()
    # Set app metainfo
    app.setApplicationName("Badger")
    icon_ref = resources.files(__name__) / "images/icon.png"
    with resources.as_file(icon_ref) as icon_path:
        app.setWindowIcon(QIcon(str(icon_path)))

    font = QFont()
    font.setPixelSize(13)
    # font.setWeight(QFont.DemiBold)
    app.setFont(font)

    # Set up stylesheet
    theme = config_singleton.read_value("BADGER_THEME")
    if theme == "dark":
        app.setStyleSheet(load_stylesheet(palette=DarkPalette))
    elif theme == "light":
        app.setStyleSheet(load_stylesheet(palette=LightPalette))
    else:
        app.setStyleSheet("")

    # Show the main window
    window = BadgerMainWindow()

    # Enable Ctrl + C quit
    signal.signal(signal.SIGINT, on_exit)
    # Let the interpreter run each 0.2 s
    timer = QtCore.QTimer()
    timer.timeout.connect(on_timeout)
    timer.start(200)

    window.show()

    # Show the saving SCORE heads-up
    # QMessageBox.information(
    #        window, 'Heads-up!', 'This might be a good time to save a SCORE.')

    sys.exit(app.exec())
