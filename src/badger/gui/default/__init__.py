from importlib import resources
import signal
import time
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtGui import QFont, QIcon
from PyQt5 import QtCore
import sys
# import ctypes
from qdarkstyle import load_stylesheet, LightPalette, DarkPalette
from ...settings import read_value
from .windows.main_window import BadgerMainWindow

# Fix the scaling issue on multiple monitors w/ different scaling settings
# if sys.platform == 'win32':
#     ctypes.windll.shcore.SetProcessDpiAwareness(1)

if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

# if hasattr(QtCore.Qt, 'HighDpiScaleFactorRoundingPolicy'):
#     QApplication.setAttribute(
#         QtCore.Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

TIMER = {'time': None}


def on_exit(*args):
    if TIMER['time'] is None:
        print('Press Ctrl/Cmd + C again within 1s to quit Badger')
        TIMER['time'] = time.time()
        return

    TIMER['time'] = None
    print('Goodbye')
    QApplication.quit()


def on_timeout():
    if TIMER['time'] is None:
        return

    now = time.time()
    if (now - TIMER['time']) > 1:
        TIMER['time'] = None
        print('Timeout, resume the operation...')


def launch_gui():
    app = QApplication(sys.argv)

    # Set app metainfo
    app.setApplicationName('Badger')
    icon_ref = resources.files(__name__) / 'images/icon.png'
    with resources.as_file(icon_ref) as icon_path:
        app.setWindowIcon(QIcon(str(icon_path)))

    font = QFont()
    font.setPixelSize(13)
    # font.setWeight(QFont.DemiBold)
    app.setFont(font)

    # Set up stylesheet
    theme = read_value('BADGER_THEME')
    if theme == 'dark':
        app.setStyleSheet(load_stylesheet(palette=DarkPalette))
    elif theme == 'light':
        app.setStyleSheet(load_stylesheet(palette=LightPalette))
    else:
        app.setStyleSheet('')

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
