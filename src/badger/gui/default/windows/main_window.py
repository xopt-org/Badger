import os
from importlib import metadata
from typing import Dict

from PyQt5.QtCore import QThread
from PyQt5.QtWidgets import QDesktopWidget, QMainWindow, QMessageBox, QStackedWidget

from badger.gui.default.components.create_process import CreateProcess
from badger.gui.default.components.process_manager import ProcessManager
from badger.gui.default.pages.home_page import BadgerHomePage


class BadgerMainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.thread_list = []
        self.process_manager = ProcessManager()
        self.process_manager.processQueueUpdated.connect(self.addSubprocess)
        self.addSubprocess()
        self.init_ui()
        self.config_logic()

    def addSubprocess(self) -> None:
        """
        Adds a subprocess to the subprocess queue.
        This method builds the subprocess on a QThread so as to not disrupt the main process.
        """
        self.thread = QThread()
        self.worker = CreateProcess()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.create_subprocess)
        self.worker.subprocess_prepared.connect(self.storeSubprocess)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.cleanupThread)

        self.thread_list.append(self.thread)
        self.thread.start()

    def cleanupThread(self) -> None:
        """
        Method to remove threads no longer active from the thread list.

        Parameters:
            thread: QThread
        """
        thread = self.sender()
        if thread in self.thread_list:
            self.thread_list.remove(thread)

    def storeSubprocess(self, process_with_args: Dict) -> None:
        """
        Store the prepared subprocess for later use.

        Parameters:
            process_with_args: Dict
        """
        self.process_manager.add_to_queue(process_with_args)

    def init_ui(self) -> None:
        version = metadata.version("badger-opt")
        version_xopt = metadata.version("xopt")
        self.setWindowTitle(f"Badger v{version} (Xopt v{version_xopt})")
        if os.getenv("DEMO"):
            self.resize(1280, 720)
        else:
            self.resize(1080, 720)
        self.center()

        # Add menu bar
        # menu_bar = self.menuBar()
        # edit_menu = menu_bar.addMenu('Edit')
        # edit_menu.addAction('New')

        # Add pages
        self.home_page = BadgerHomePage(self.process_manager)

        self.stacks = stacks = QStackedWidget()
        stacks.addWidget(self.home_page)

        stacks.setCurrentIndex(0)

        self.setCentralWidget(self.stacks)

    def center(self) -> None:
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()

        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def config_logic(self) -> None:
        pass

    def closeEvent(self, event) -> None:
        monitor = self.home_page.run_monitor
        if not monitor.running:
            self.process_manager.close_proccesses()
            monitor.destroy_unused_env()
            return

        reply = QMessageBox.question(
            self,
            "Window Close",
            "Closing this window will terminate the current run, "
            "and the run data would be archived.\n\nProceed?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply == QMessageBox.Yes:

            def close_window():
                monitor.destroy_unused_env()
                self.close()

            monitor.register_post_run_action(close_window)
            monitor.testing = True  # suppress the archive pop-ups
            monitor.routine_runner.stop_routine()
            event.ignore()
        else:
            event.ignore()
