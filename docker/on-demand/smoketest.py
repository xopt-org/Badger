"""Smoke test: verify PyQt5 can create a window inside Xvfb."""

import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
from PyQt5.QtCore import QTimer


def main():
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Badger Smoke Test")
    window.setCentralWidget(QLabel("PyQt5 is rendering inside Xvfb!"))
    window.resize(400, 200)
    window.show()

    # Quit after 2 seconds — proves the event loop runs and renders
    QTimer.singleShot(2000, app.quit)
    exit_code = app.exec_()

    if exit_code == 0:
        print("SMOKE TEST PASSED: PyQt5 renders correctly in Xvfb")
    else:
        print(f"SMOKE TEST FAILED: exit code {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
