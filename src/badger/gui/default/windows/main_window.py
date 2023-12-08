import os
import time
from importlib import metadata
from PyQt5.QtWidgets import QMainWindow, QStackedWidget, QDesktopWidget
from PyQt5.QtWidgets import QMessageBox
# from PyQt5.QtWidgets import QMenuBar, QMenu
from ..pages.home_page import BadgerHomePage


class BadgerMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.init_ui()
        self.config_logic()

    def init_ui(self):
        version = metadata.version('badger-opt')
        version_xopt = metadata.version('xopt')
        self.setWindowTitle(f'Badger v{version} (Xopt v{version_xopt})')
        if os.getenv('DEMO'):
            self.resize(1280, 720)
        else:
            self.resize(960, 720)
        self.center()

        # Add menu bar
        # menu_bar = self.menuBar()
        # edit_menu = menu_bar.addMenu('Edit')
        # edit_menu.addAction('New')

        # Add pages
        self.home_page = BadgerHomePage()

        self.stacks = stacks = QStackedWidget()
        stacks.addWidget(self.home_page)

        stacks.setCurrentIndex(0)

        self.setCentralWidget(self.stacks)

    def center(self):
        qr = self.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()

        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def config_logic(self):
        pass

    def closeEvent(self, event):
        monitor = self.home_page.run_monitor
        if not monitor.running:
            monitor.destroy_unused_env()
            return

        reply = QMessageBox.question(
            self, 'Window Close',
            'Closing this window will terminate the current run, '
            'and the run data would be archived.\n\nProceed?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            def close_window():
                monitor.destroy_unused_env()
                self.close()

            monitor.register_post_run_action(close_window)
            monitor.testing = True  # suppress the archive pop-ups
            monitor.btn_stop.click()
            event.ignore()
        else:
            event.ignore()
