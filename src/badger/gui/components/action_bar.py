from PyQt5.QtWidgets import QWidget, QHBoxLayout
from PyQt5.QtWidgets import QToolButton, QMenu, QAction
from PyQt5.QtGui import QIcon, QFont
from PyQt5.QtCore import pyqtSignal
from importlib import resources
from badger.gui.utils import create_button

stylesheet_del = """
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

stylesheet_log = """
QPushButton:hover:pressed
{
    background-color: #88C0D0;
}
QPushButton:hover
{
    background-color: #72A4B4;
}
QPushButton
{
    background-color: #5C8899;
    color: #000000;
}
"""

stylesheet_ext = """
QPushButton:hover:pressed
{
    background-color: #4DB6AC;
}
QPushButton:hover
{
    background-color: #26A69A;
}
QPushButton
{
    background-color: #00897B;
}
"""

stylesheet_run = """
QToolButton:hover:pressed
{
    background-color: #92D38C;
}
QToolButton:hover
{
    background-color: #6EC566;
}
QToolButton
{
    background-color: #4AB640;
    color: #000000;
}
"""

stylesheet_stop = """
QToolButton:hover:pressed
{
    background-color: #C7737B;
}
QToolButton:hover
{
    background-color: #BF616A;
}
QToolButton
{
    background-color: #A9444E;
}
"""


class BadgerActionBar(QWidget):
    sig_start = pyqtSignal()
    sig_start_until = pyqtSignal()
    sig_stop = pyqtSignal()

    sig_delete_run = pyqtSignal()
    sig_logbook = pyqtSignal()
    sig_reset_env = pyqtSignal()
    sig_jump_to_optimal = pyqtSignal()
    sig_dial_in = pyqtSignal()
    sig_ctrl = pyqtSignal(bool)
    sig_open_extensions_palette = pyqtSignal()

    sig_save_checkpoint = pyqtSignal()
    sig_edit_checkpoint = pyqtSignal()
    sig_load_checkpoint = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.config_logic()

    def init_ui(self):
        def load_internal_icon(name: str) -> QIcon:
            icon_ref = resources.files(__package__) / f"../images/{name}"
            with resources.as_file(icon_ref) as icon_path:
                return QIcon(str(icon_path))

        self.icon_play = load_internal_icon("play.png")
        self.icon_pause = load_internal_icon("pause.png")
        self.icon_stop = load_internal_icon("stop.png")
        self.icon_flag = load_internal_icon("flag.png")
        self.icon_flag_up = load_internal_icon("flag_up.png")
        self.icon_flag_down = load_internal_icon("flag_down.png")

        hbox_action = QHBoxLayout(self)
        hbox_action.setContentsMargins(0, 0, 0, 0)

        # Background widget
        self.bg = QWidget()
        hbox_action.addWidget(self.bg, 1)
        self.bg.setObjectName("ActionBar")
        hbox_bg = QHBoxLayout(self.bg)
        hbox_bg.setContentsMargins(8, 8, 8, 8)

        cool_font = QFont()
        cool_font.setWeight(QFont.DemiBold)
        cool_font.setPixelSize(13)

        self.btn_del = create_button("trash.png", "Delete run", stylesheet_del)
        self.btn_log = create_button("book.png", "Logbook", stylesheet_log)
        self.btn_reset = create_button("undo.png", "Reset environment")
        self.btn_checkpoint = create_button(
            "flag.png", "Checkpoint", size=(48, 32), tool_button=True
        )
        self.btn_opt = create_button("star.png", "Jump to optimum")
        self.btn_set = create_button("set.png", "Dial in solution")
        self.btn_ctrl = create_button("pause.png", "Pause")
        self.btn_ctrl._status = "pause"

        self.btn_del.setDisabled(True)
        self.btn_log.setDisabled(True)
        self.btn_reset.setDisabled(True)
        self.btn_checkpoint.setDisabled(True)
        self.btn_opt.setDisabled(True)
        self.btn_set.setDisabled(True)
        self.btn_ctrl.setDisabled(True)

        # self.btn_stop = btn_stop = QPushButton('Run')
        self.btn_stop = QToolButton()
        self.btn_stop.setFixedSize(96, 32)
        self.btn_stop.setFont(cool_font)
        self.btn_stop.setStyleSheet(stylesheet_run)

        # add button for extensions
        self.btn_open_extensions_palette = btn_extensions = create_button(
            "extension.png", "Open extensions", stylesheet_ext
        )

        # Create a menu and add options
        self.checkpoint_menu = checkpoint_menu = QMenu(self)
        checkpoint_menu.setFixedWidth(128)
        self.save_checkpoint_action = save_checkpoint_action = QAction(
            self.icon_flag_down, "Save Checkpoint", self
        )
        self.edit_checkpoint_action = edit_checkpoint_action = QAction(
            self.icon_flag, "Edit Checkpoint", self
        )
        self.load_checkpoint_action = load_checkpoint_action = QAction(
            self.icon_flag_up, "Load Checkpoint", self
        )
        checkpoint_menu.addAction(save_checkpoint_action)
        checkpoint_menu.addAction(edit_checkpoint_action)
        checkpoint_menu.addAction(load_checkpoint_action)

        # Set the menu as the checkpoint button's dropdown menu
        self.btn_checkpoint.setMenu(checkpoint_menu)
        self.btn_checkpoint.setDefaultAction(save_checkpoint_action)
        self.btn_checkpoint.setPopupMode(QToolButton.MenuButtonPopup)

        # Create a menu and add options
        self.run_menu = menu = QMenu(self)
        menu.setFixedWidth(128)
        self.run_action = run_action = QAction("Run", self)
        run_action.setIcon(self.icon_play)
        self.run_until_action = run_until_action = QAction("Run until", self)
        run_until_action.setIcon(self.icon_play)
        menu.addAction(run_action)
        menu.addAction(run_until_action)

        # Set the menu as the run button's dropdown menu
        self.btn_stop.setMenu(menu)
        self.btn_stop.setDefaultAction(run_action)
        self.btn_stop.setPopupMode(QToolButton.MenuButtonPopup)
        self.btn_stop.setDisabled(False)
        # btn_stop.setToolTip('')

        # Config button
        self.btn_config = btn_config = create_button("tools.png", "Configure run")
        btn_config.hide()

        hbox_bg.addWidget(self.btn_del)
        # hbox_action.addWidget(btn_edit)
        hbox_bg.addWidget(self.btn_log)
        hbox_bg.addStretch(1)
        hbox_bg.addWidget(self.btn_reset)
        hbox_bg.addWidget(self.btn_ctrl)
        hbox_bg.addWidget(self.btn_stop)
        hbox_bg.addWidget(self.btn_checkpoint)
        hbox_bg.addWidget(self.btn_opt)
        hbox_bg.addWidget(self.btn_set)
        hbox_bg.addStretch(1)
        hbox_bg.addWidget(btn_extensions)
        hbox_bg.addWidget(btn_config)

        self.setStyleSheet("""
            #ActionBar {
                background-color: #455364;
            }
        """)

    def config_logic(self):
        self.btn_del.clicked.connect(self.delete_run)
        self.btn_log.clicked.connect(self.logbook)
        self.btn_reset.clicked.connect(self.reset_env)
        self.btn_opt.clicked.connect(self.jump_to_optimal)
        self.btn_set.clicked.connect(self.dial_in)
        self.btn_ctrl.clicked.connect(self.ctrl_routine)
        self.run_action.triggered.connect(self.set_run_action)
        self.run_until_action.triggered.connect(self.set_run_until_action)
        self.save_checkpoint_action.triggered.connect(
            lambda: self.sig_save_checkpoint.emit()
        )
        self.edit_checkpoint_action.triggered.connect(
            lambda: self.sig_edit_checkpoint.emit()
        )
        self.load_checkpoint_action.triggered.connect(
            lambda: self.sig_load_checkpoint.emit()
        )
        self.btn_open_extensions_palette.clicked.connect(self.open_extensions_palette)

    def lock(self):
        self.btn_del.setDisabled(True)
        self.btn_log.setDisabled(True)
        self.btn_reset.setDisabled(True)
        self.btn_checkpoint.setDisabled(True)
        self.btn_ctrl.setDisabled(True)
        self.btn_stop.setDisabled(True)
        self.btn_opt.setDisabled(True)
        self.btn_set.setDisabled(True)

    def unlock(self):
        self.btn_del.setDisabled(False)
        self.btn_log.setDisabled(False)
        self.btn_reset.setDisabled(False)
        self.btn_checkpoint.setDisabled(False)
        self.btn_ctrl.setDisabled(False)
        self.btn_stop.setDisabled(False)
        self.btn_opt.setDisabled(False)
        self.btn_set.setDisabled(False)

    def routine_invalid(self):
        self.btn_stop.setDisabled(False)

    def routine_finished(self):
        self.btn_ctrl.setIcon(self.icon_pause)
        self.btn_ctrl.setToolTip("Pause")
        self.btn_ctrl._status = "pause"
        self.btn_ctrl.setDisabled(True)

        # Note the order of the following two lines cannot be changed!
        self.btn_stop.setPopupMode(QToolButton.MenuButtonPopup)
        self.btn_stop.setStyleSheet(stylesheet_run)
        self.run_action.setText("Run")
        self.run_action.setIcon(self.icon_play)
        self.run_until_action.setText("Run until")
        self.run_until_action.setIcon(self.icon_play)
        # self.btn_stop.setToolTip('')
        self.btn_stop.setDisabled(False)

        self.btn_reset.setDisabled(False)
        self.btn_set.setDisabled(False)
        self.btn_del.setDisabled(False)

    def toggle_reset(self, locked):
        self.btn_reset.setDisabled(locked)

    def toggle_run(self, locked):
        self.btn_stop.setDisabled(locked)

    def toggle_other(self, locked):
        self.btn_del.setDisabled(locked)
        self.btn_log.setDisabled(locked)
        self.btn_opt.setDisabled(locked)
        self.btn_set.setDisabled(locked)

    def run_start(self):
        self.btn_stop.setStyleSheet(stylesheet_stop)
        self.btn_stop.setPopupMode(QToolButton.DelayedPopup)
        self.btn_stop.setDisabled(False)
        self.run_action.setText("Stop")
        self.run_action.setIcon(self.icon_stop)
        self.run_until_action.setText("Stop")
        self.run_until_action.setIcon(self.icon_stop)
        self.btn_checkpoint.setDisabled(False)
        self.btn_ctrl.setDisabled(False)
        self.btn_set.setDisabled(True)

    def set_run_action(self):
        if self.btn_stop.defaultAction() is not self.run_action:
            self.btn_stop.setDefaultAction(self.run_action)

        if self.run_action.text() == "Run":
            self.btn_stop.setDisabled(True)
            self.sig_start.emit()
        else:
            self.btn_stop.setDisabled(True)
            self.sig_stop.emit()

    def set_run_until_action(self):
        if self.btn_stop.defaultAction() is not self.run_until_action:
            self.btn_stop.setDefaultAction(self.run_until_action)

        if self.run_until_action.text() == "Run until":
            self.sig_start_until.emit()
        else:
            self.btn_stop.setDisabled(True)
            self.sig_stop.emit()

    def delete_run(self):
        self.sig_delete_run.emit()

    def logbook(self):
        self.sig_logbook.emit()

    def reset_env(self):
        self.sig_reset_env.emit()

    def jump_to_optimal(self):
        self.sig_jump_to_optimal.emit()

    def dial_in(self):
        self.sig_dial_in.emit()

    def ctrl_routine(self):
        if self.btn_ctrl._status == "pause":
            self.sig_ctrl.emit(True)
            self.btn_ctrl.setIcon(self.icon_play)
            self.btn_ctrl.setToolTip("Resume")
            self.btn_ctrl._status = "play"
        else:
            self.sig_ctrl.emit(False)
            self.btn_ctrl.setIcon(self.icon_pause)
            self.btn_ctrl.setToolTip("Pause")
            self.btn_ctrl._status = "pause"

    def open_extensions_palette(self):
        self.sig_open_extensions_palette.emit()

    def env_ready(self):
        self.btn_log.setDisabled(False)
        self.btn_opt.setDisabled(False)
