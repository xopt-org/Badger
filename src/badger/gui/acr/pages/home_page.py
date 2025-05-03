import gc
import traceback
from importlib import resources

from pandas import DataFrame
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QIcon, QKeySequence
from PyQt5.QtWidgets import (
    QMessageBox,
    QShortcut,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QLabel,
)

from badger.archive import (
    delete_run,
    get_base_run_filename,
    load_run,
    get_runs,
    save_tmp_run,
)
from badger.gui.default.components.data_table import (
    add_row,
    data_table,
    reset_table,
    update_table,
)
from badger.gui.acr.components.history_navigator import HistoryNavigator
from badger.gui.acr.components.routine_editor import BadgerRoutineEditor
from badger.gui.default.components.run_monitor import BadgerOptMonitor
from badger.gui.acr.components.status_bar import BadgerStatusBar
from badger.gui.acr.components.action_bar import BadgerActionBar
from badger.utils import get_header
from badger.settings import init_settings

# from PyQt5.QtGui import QBrush, QColor
from badger.gui.default.windows.message_dialog import BadgerScrollableMessageBox
from badger.gui.default.utils import ModalOverlay

import logging

logger = logging.getLogger(__name__)

stylesheet = """
QPushButton:hover:pressed
{
    background-color: #C7737B;
}
QPushButton:hover
{
    background-color: #BF616A;
}
QPushButton
{
    background-color: #A9444E;
}
"""


class BadgerHomePage(QWidget):
    sig_routine_activated = pyqtSignal(bool)
    sig_routine_invalid = pyqtSignal()

    def __init__(self, process_manager=None):
        super().__init__()

        self.mode = "regular"  # home page mode
        self.splitter_state = None  # store the run splitter state
        self.process_manager = process_manager
        self.current_routine = None  # current routine
        self.go_run_failed = False  # flag to indicate go_run failed
        self.init_ui()
        self.config_logic()

        self.load_all_runs()
        self.init_home_page()

    def init_ui(self):
        self.config_singleton = init_settings()
        icon_ref = resources.files(__package__) / "../images/add.png"

        with resources.as_file(icon_ref) as icon_path:
            self.icon_add = QIcon(str(icon_path))
        icon_ref = resources.files(__package__) / "../images/import.png"
        with resources.as_file(icon_ref) as icon_path:
            self.icon_import = QIcon(str(icon_path))
        icon_ref = resources.files(__package__) / "../images/export.png"
        with resources.as_file(icon_ref) as icon_path:
            self.icon_export = QIcon(str(icon_path))

        # Set up the layout
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        # History run browser
        self.history_browser = history_browser = HistoryNavigator()
        history_browser.setFixedWidth(360)

        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        vbox.addWidget(splitter, 1)

        # Monitor panel
        panel_monitor = QWidget()
        vbox_monitor = QVBoxLayout(panel_monitor)
        vbox_monitor.setContentsMargins(8, 0, 8, 0)

        # Run monitor
        self.run_view = run_view = QWidget()  # for consistent bg
        vbox_monitor.addWidget(run_view)
        vbox_run_view = QVBoxLayout(run_view)
        vbox_run_view.setContentsMargins(0, 0, 0, 10)
        self.run_monitor = run_monitor = BadgerOptMonitor(self.process_manager)
        vbox_run_view.addWidget(run_monitor)

        # Data table
        panel_table = QWidget()
        panel_table.setMinimumHeight(180)
        vbox_table = QVBoxLayout(panel_table)
        vbox_table.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel("Run Data")
        title_label.setStyleSheet(
            """
            background-color: #455364;
            font-weight: bold;
            padding: 4px;
        """
        )
        title_label.setAlignment(Qt.AlignCenter)  # Center-align the title
        vbox_table.addWidget(title_label, 0)
        self.run_table = run_table = data_table()
        run_table.set_uneditable()  # should not be editable
        vbox_table.addWidget(run_table, 1)

        # Routine view
        self.routine_view = routine_view = QWidget()  # for consistent bg
        routine_view.setMinimumWidth(640)
        vbox_routine_view = QVBoxLayout(routine_view)
        vbox_routine_view.setContentsMargins(0, 0, 0, 10)
        self.routine_editor = routine_editor = BadgerRoutineEditor()
        vbox_routine_view.addWidget(routine_editor)

        # Add action bar
        self.run_action_bar = run_action_bar = BadgerActionBar()

        # Run panel (routine editor + run monitor + data table + action bar)
        panel_run = QWidget()
        vbox_run = QVBoxLayout(panel_run)
        vbox_run.setContentsMargins(0, 0, 0, 0)
        vbox_run.setSpacing(0)

        splitter_run = QSplitter(Qt.Horizontal)
        splitter_run.setStretchFactor(0, 1)
        splitter_run.setStretchFactor(1, 1)
        vbox_run.addWidget(splitter_run, 1)

        splitter_data = QSplitter(Qt.Vertical)
        splitter_data.setStretchFactor(0, 1)
        splitter_data.setStretchFactor(1, 0)
        splitter_data.addWidget(panel_monitor)
        splitter_data.addWidget(panel_table)

        splitter_run.addWidget(routine_view)
        splitter_run.addWidget(splitter_data)

        vbox_run.addWidget(run_action_bar, 0)

        # Add panels to splitter
        splitter.addWidget(history_browser)
        splitter.addWidget(panel_run)

        # Set initial sizes (left fixed, middle and right equal)
        splitter.setSizes([1, 1])
        splitter_run.setSizes([1, 1])
        splitter_data.setSizes([800, 180])

        self.status_bar = status_bar = BadgerStatusBar()
        status_bar.set_summary("Badger is ready!")
        vbox.addWidget(status_bar)

    def config_logic(self):
        self.colors = ["c", "g", "m", "y", "b", "r", "w"]
        self.symbols = ["o", "t", "t1", "s", "p", "h", "d"]

        self.run_table.cellClicked.connect(self.solution_selected)
        self.run_table.itemSelectionChanged.connect(self.table_selection_changed)

        self.history_browser.tree_widget.itemSelectionChanged.connect(self.go_run)

        self.routine_editor.routine_page.sig_load_template.connect(self.update_status)
        self.routine_editor.routine_page.sig_save_template.connect(self.update_status)

        self.run_monitor.sig_inspect.connect(self.inspect_solution)
        self.run_monitor.sig_lock.connect(self.toggle_lock)
        self.run_monitor.sig_new_run.connect(self.new_run)
        self.run_monitor.sig_run_started.connect(self.uncover_page)
        self.run_monitor.sig_run_name.connect(self.run_name)
        self.run_monitor.sig_status.connect(self.update_status)
        self.run_monitor.sig_progress.connect(self.progress)
        self.run_monitor.sig_del.connect(self.delete_run)
        self.run_monitor.sig_stop_run.connect(self.cover_page)
        self.run_monitor.sig_run_started.connect(self.run_action_bar.run_start)
        self.run_monitor.sig_routine_finished.connect(
            self.run_action_bar.routine_finished
        )
        self.run_monitor.sig_lock_action.connect(self.run_action_bar.lock)
        self.run_monitor.sig_toggle_reset.connect(self.run_action_bar.toggle_reset)
        self.run_monitor.sig_toggle_run.connect(self.run_action_bar.toggle_run)
        self.run_monitor.sig_toggle_other.connect(self.run_action_bar.toggle_other)
        self.run_monitor.sig_env_ready.connect(self.run_action_bar.env_ready)

        self.run_action_bar.sig_start.connect(self.start_run)
        self.run_action_bar.sig_start_until.connect(self.start_run_until)
        self.run_action_bar.sig_stop.connect(self.run_monitor.stop)
        self.run_action_bar.sig_delete_run.connect(self.run_monitor.delete_run)
        self.run_action_bar.sig_logbook.connect(self.run_monitor.logbook)
        self.run_action_bar.sig_reset_env.connect(self.run_monitor.reset_env)
        self.run_action_bar.sig_jump_to_optimal.connect(
            self.run_monitor.jump_to_optimal
        )
        self.run_action_bar.sig_dial_in.connect(self.run_monitor.set_vars)
        self.run_action_bar.sig_ctrl.connect(self.run_monitor.ctrl_routine)
        self.run_action_bar.sig_open_extensions_palette.connect(
            self.run_monitor.open_extensions_palette
        )

        self.sig_routine_invalid.connect(self.run_action_bar.routine_invalid)

        # Assign shortcuts
        self.shortcut_go_search = QShortcut(QKeySequence("Ctrl+L"), self)
        self.shortcut_go_search.activated.connect(self.go_search)

    def go_search(self):
        self.sbar.setFocus()

    def load_all_runs(self):
        runs = get_runs()
        self.history_browser.updateItems(runs)

    def init_home_page(self):
        # Load the default generator
        self.routine_editor.routine_page.generator_box.cb.setCurrentIndex(0)

    def go_run(self, i: int = None):
        gc.collect()

        # if self.cb_history.itemText(0) == "Optimization in progress...":
        #     return

        if i == -1:
            update_table(self.run_table)
            try:
                self.current_routine.data = None  # reset the data
            except AttributeError:  # current routine is None
                pass
            self.run_monitor.init_plots(self.current_routine)
            if not self.current_routine:
                self.routine_editor.set_routine(None)
                self.status_bar.set_summary("No active routine")
            else:
                self.status_bar.set_summary(
                    f"Current routine: {self.current_routine.name}"
                )
            return

        run_filename = get_base_run_filename(self.history_browser.currentText())
        try:
            routine = load_run(run_filename)
            self.run_monitor.routine_filename = run_filename
        except IndexError:
            return
        except Exception as e:  # failed to load the run
            details = traceback.format_exc()
            dialog = BadgerScrollableMessageBox(
                title="Error!", text=str(e), parent=self
            )
            dialog.setIcon(QMessageBox.Critical)
            dialog.setDetailedText(details)
            dialog.exec_()
            self.go_run_failed = True

            # Show info in the nav bar
            # red_brush = QBrush(QColor(255, 0, 0))  # red color
            # self.cb_history.changeCurrentItem(
            #     f"{run_filename} (failed to load)",
            #     # color=red_brush)
            #     color=None,
            # )

            return

        self.current_routine = routine  # update the current routine
        update_table(self.run_table, routine.sorted_data)
        self.run_monitor.init_plots(routine, run_filename)
        self.routine_editor.set_routine(routine, silent=True)
        self.status_bar.set_summary(f"Current routine: {self.current_routine.name}")

        self.run_monitor.update_analysis_extensions()

    def inspect_solution(self, idx):
        self.run_table.selectRow(idx)

    def solution_selected(self, r, c):
        self.run_monitor.jump_to_solution(r)

    def table_selection_changed(self):
        indices = self.run_table.selectedIndexes()
        if len(indices) == 1:  # let other method handles it
            return

        row = -1
        for index in indices:
            _row = index.row()
            if _row == row:
                continue

            if row == -1:
                row = _row
                continue

            return

        if row == -1:
            return

        self.run_monitor.jump_to_solution(row)

    def toggle_lock(self, lock, lock_tab=1):
        if lock:
            self.history_browser.setDisabled(True)
        else:
            self.history_browser.setDisabled(False)

            self.uncover_page()

    def prepare_run(self):
        try:
            routine = self.routine_editor.routine_page._compose_routine()
        except Exception as e:
            self.sig_routine_invalid.emit()
            raise e

        self.current_routine = routine

        # Save routine as a temp file
        # since routine runner subprocess needs to load routine from file
        run_filename = save_tmp_run(routine)
        self.run_monitor.routine_filename = run_filename

        # Tell monitor to start the run
        self.run_monitor.init_plots(routine)

    def start_run(self):
        self.prepare_run()
        self.run_monitor.start()

    def start_run_until(self):
        self.prepare_run()
        self.run_monitor.start_until()

    def new_run(self):
        self.cover_page()

        # self.cb_history.insertItem(0, "Optimization in progress...")
        # self.cb_history.setCurrentIndex(0)

        header = get_header(self.current_routine)
        reset_table(self.run_table, header)

    def run_name(self, name):
        runs = get_runs()
        self.history_browser.updateItems(runs)
        self.history_browser._selectItemByRun(name)

    def update_status(self, info):
        self.status_bar.set_summary(info)

    def progress(self, solution: DataFrame):
        vocs = self.current_routine.vocs
        vars = list(solution[vocs.variable_names].to_numpy()[0])
        objs = list(solution[vocs.objective_names].to_numpy()[0])
        cons = list(solution[vocs.constraint_names].to_numpy()[0])
        stas = list(solution[vocs.observable_names].to_numpy()[0])
        add_row(self.run_table, objs + cons + vars + stas)

    def delete_run(self):
        run_name = get_base_run_filename(self.history_browser.currentText())

        reply = QMessageBox.question(
            self,
            "Delete run",
            f"Are you sure you want to delete run {run_name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        delete_run(run_name)
        runs = get_runs()
        self.history_browser.tree_widget.blockSignals(True)
        self.history_browser.updateItems(runs)
        self.history_browser.tree_widget.blockSignals(False)
        self.go_run(-1)

    def cover_page(self):
        return  # disable overlay for now

        try:
            self.overlay
        except AttributeError:
            # Set parent to the main window
            try:
                main_window = self.parent().parent()
            except AttributeError:  # in test mode
                return
            self.overlay = ModalOverlay(main_window)
        self.overlay.show()

    def uncover_page(self):
        return  # disable overlay for now

        try:
            self.overlay.hide()
        except AttributeError:  # in test mode
            pass
