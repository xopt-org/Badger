"""The top-level window. Contains the home page and manages the subprocess
pool for optimization runs. Handles graceful shutdown when closed."""

import logging
import os
from importlib import metadata

from PyQt5.QtCore import QThread
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import QDesktopWidget, QMainWindow, QMessageBox, QStackedWidget

from badger.gui.components.create_process import CreateProcess
from badger.gui.components.process_manager import ProcessManager
from badger.gui.pages.home_page import BadgerHomePage
from badger.types import ProcessWithArgs

logger = logging.getLogger(__name__)


class BadgerMainWindow(QMainWindow):
    def __init__(self) -> None:
        logger.info("Initializing BadgerMainWindow.")
        super().__init__()
        self.thread_list: list[QThread] = []
        self.process_manager = ProcessManager()
        self.process_manager.processQueueUpdated.connect(self.addSubprocess)
        self.addSubprocess()
        self.init_ui()
        self.config_logic()

    def addSubprocess(self) -> None:
        logger.info("Adding subprocess to queue.")
        """
        Adds a subprocess to the subprocess queue.
        This method builds the subprocess on a QThread so as to not disrupt the main process.
        """
        self._thread = QThread()
        self.worker = CreateProcess()
        self.worker.moveToThread(self._thread)

        self._thread.started.connect(self.worker.create_subprocess)
        self.worker.subprocess_prepared.connect(self.storeSubprocess)
        self.worker.finished.connect(self._thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self.cleanupThread)

        self.thread_list.append(self._thread)
        self._thread.start()

    def cleanupThread(self) -> None:
        logger.info("Cleaning up finished thread.")
        """
        Method to remove threads no longer active from the thread list.

        Parameters:
            None
        The thread to be cleaned up is inferred from the sender of the signal.
        """
        thread = self.sender()
        if thread in self.thread_list:
            self.thread_list.remove(thread)

    def storeSubprocess(self, process_with_args: ProcessWithArgs) -> None:
        logger.info(f"Storing prepared subprocess: {process_with_args}")
        """
        Store the prepared subprocess for later use.

        Parameters:
            process_with_args: ProcessWithArgs
        """
        self.process_manager.add_to_queue(process_with_args)

    def init_ui(self) -> None:
        logger.info("Initializing UI.")
        version = metadata.version("badger-opt")
        version_xopt = metadata.version("xopt")
        self.setWindowTitle(f"Badger v{version} (Xopt v{version_xopt})")
        if os.getenv("DEMO"):
            self.resize(1280, 720)
        else:
            self.resize(1720, 960)
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
        logger.info("Centering main window.")
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()

        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def config_logic(self) -> None:
        logger.info("Configuring logic.")

    def closeEvent(self, event: QCloseEvent | None) -> None:
        logger.info("Main window close event triggered.")
        if (
            hasattr(self.home_page.routine_editor, "archive_search")
            and self.home_page.routine_editor.archive_search.isVisible()
        ):
            self.home_page.routine_editor.archive_search.close()

        monitor = self.home_page.run_monitor
        if not monitor.running:
            self.process_manager.close_processes()
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

            def close_window() -> None:
                monitor.destroy_unused_env()
                self.close()

            monitor.register_post_run_action(close_window)
            monitor.testing = True  # suppress the archive pop-ups
            if monitor.routine_runner is not None:
                monitor.routine_runner.stop_routine()

        if event is not None:
            event.ignore()
