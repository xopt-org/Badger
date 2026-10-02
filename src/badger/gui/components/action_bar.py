"""Toolbar with run-control buttons (start, pause, stop), logbook submission,
docs access, and the extensions palette launcher."""

from importlib import resources

from PyQt5.QtCore import QEvent, QPoint, QSize, Qt, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPainter, QPaintEvent, QPalette
from PyQt5.QtWidgets import (
    QAction,
    QHBoxLayout,
    QMenu,
    QStyle,
    QStyleOptionToolButton,
    QToolButton,
    QWidget,
)

from badger.gui.utils import create_button
from badger.gui.windows.docs_window import BadgerDocsWindow


class SplitTooltipToolButton(QToolButton):
    """
    QToolButton that shows a separate tooltip over the dropdown-arrow area.
    Use arg menu_tooltip="desired tooltip" to set the menu tooltip
    """

    def __init__(self, menu_tooltip: str = "", parent=None):
        """
        Parameters
        ----------
        menu_tooltip (str)
            tooltip for menu
        """
        super().__init__(parent)
        self.menu_tooltip = menu_tooltip
        self.display_text: str | None = None  # show next termination condition
        self._last_display_text: str | None = (
            None  # used to show/hide text while running
        )

        font = QFont()
        font.setWeight(QFont.Normal)
        font.setPixelSize(10)
        self.setFont(font)

    def setDisplayText(self, text: str) -> None:
        self.display_text = text
        self.update()

    def setDefaultAction(self, action: QAction) -> None:
        super().setDefaultAction(action)
        self.setIcon(action.icon())
        self.update()

    def hide_text(self) -> None:
        self._last_display_text = self.display_text
        self.setDisplayText("")

    def show_text(self) -> None:
        self.setDisplayText(self._last_display_text)

    def initStyleOption(self, option) -> None:
        super().initStyleOption(option)
        if self.display_text is not None:
            option.text = self.display_text

    def paintEvent(self, event: QPaintEvent) -> None:
        option = QStyleOptionToolButton()
        self.initStyleOption(option)
        painter = QPainter(self)
        option.text = ""
        option.toolButtonStyle = Qt.ToolButtonIconOnly
        self.style().drawComplexControl(QStyle.CC_ToolButton, option, painter, self)
        painter.setFont(self.font())
        painter.setPen(option.palette.color(QPalette.ButtonText))
        text_rect = self.rect().adjusted(self.width() // 2 - 4, 14, -8, 0)
        painter.drawText(
            text_rect, Qt.AlignLeft | Qt.AlignVCenter, self.display_text or ""
        )

    def _over_menu_arrow(self, pos: QPoint) -> bool:
        opt = QStyleOptionToolButton()
        self.initStyleOption(opt)
        rect = self.style().subControlRect(
            QStyle.CC_ToolButton, opt, QStyle.SC_ToolButtonMenu, self
        )
        return rect.contains(pos)

    def event(self, event: QEvent) -> bool:
        if event.type() == QEvent.ToolTip and self._over_menu_arrow(event.pos()):
            from PyQt5.QtWidgets import QToolTip

            QToolTip.showText(event.globalPos(), self.menu_tooltip, self)
            return True
        return super().event(event)


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
    color: #FFFFFF;
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
    sig_start_until = pyqtSignal(  # I think this is now deprecated
        bool
    )  # bool True launches termination condition dialog menu
    sig_stop = pyqtSignal()
    sig_flag_restart = pyqtSignal()
    sig_delete_run = pyqtSignal()
    sig_logbook = pyqtSignal()
    sig_reset_env = pyqtSignal()
    sig_jump_to_optimal = pyqtSignal()
    sig_dial_in = pyqtSignal()
    sig_ctrl = pyqtSignal(bool)
    sig_run_with_data = pyqtSignal()
    sig_smart_run_ctrl = pyqtSignal()
    sig_open_extensions_palette = pyqtSignal()
    # signal to home_page to open termination edit dialog
    sig_update_tc = pyqtSignal()

    sig_save_checkpoint = pyqtSignal()
    sig_edit_checkpoint = pyqtSignal()
    sig_load_checkpoint = pyqtSignal()

    def __init__(self, parent: QWidget | None = None, minimode: bool = False) -> None:
        super().__init__(parent)
        self.mini_mode = minimode
        self.docs_name = "gui-usage"
        self.init_ui()
        self.config_logic()

    def init_ui(self) -> None:
        def load_internal_icon(name: str) -> QIcon:
            icon_ref = resources.files(__package__) / f"../images/{name}"
            with resources.as_file(icon_ref) as icon_path:
                return QIcon(str(icon_path))

        self.icon_play = load_internal_icon("play.png")
        self.icon_play_time = load_internal_icon("play_time.png")
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

        self.btn_del = create_button("trash.png", "Delete run", stylesheet_del)
        self.btn_log = create_button("book.png", "Logbook", stylesheet_log)
        self.btn_help = create_button("help_btn.png", "Open Docs", stylesheet_log)
        self.btn_help.setIconSize(QSize(20, 20))

        self.btn_reset = create_button("undo.png", "Reset environment")
        self.btn_checkpoint = create_button(
            "flag.png", "Checkpoint", size=(48, 32), tool_button=True
        )
        self.btn_opt = create_button("star.png", "Jump to optimum")
        self.btn_set = create_button("set.png", "Dial in solution")

        self.btn_del.setDisabled(True)
        self.btn_log.setDisabled(True)
        self.btn_reset.setDisabled(True)
        self.btn_checkpoint.setDisabled(True)
        self.btn_opt.setDisabled(True)
        self.btn_set.setDisabled(True)

        # self.btn_stop = btn_stop = QPushButton('Run')
        self.btn_stop = SplitTooltipToolButton(menu_tooltip="Run Options Menu")
        self.btn_stop.setFixedSize(96, 32)
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

        # TODO: This is quite clunky, the run button (btn_stop) should really have
        # its own class with action/signal/ui logic.
        if self.mini_mode:
            # In 'mini mode', the action is always smart_run_action. Selecting either
            # "New Run" or "Edit Condition" from the menu will emit signals to
            # perform the associated actions, but do not update the default
            self.run_action = run_action = QAction("New Run", self)
            run_action.setIcon(self.icon_play)
            self.run_until_action = run_until_action = QAction("Run until", self)
            run_until_action.setIcon(self.icon_play_time)
            self.run_until_menu_action = run_until_menu_action = QAction(
                "Edit Condition", self
            )
            run_until_menu_action.setIcon(self.icon_play_time)
            self.smart_run_action = smart_run_action = QAction("Run", self)
            smart_run_action.setIcon(self.icon_play)

            self.stop_run_action = QAction("Stop", self)
            self.stop_run_action.setIcon(self.icon_stop)

            menu.addAction(run_action)
            menu.addAction(run_until_menu_action)
        else:
            # In non-mini mode, selecting "Run until" or "Run" from the
            # menu will update the default run action.
            self.run_action = run_action = QAction("New Run", self)
            run_action.setIcon(self.icon_play)
            self.run_until_action = run_until_action = QAction("Run until", self)
            run_until_action.setIcon(self.icon_play_time)
            self.run_until_menu_action = run_until_menu_action = QAction(
                "Run until", self
            )
            run_until_menu_action.setIcon(self.icon_play_time)
            self.smart_run_action = smart_run_action = QAction(
                "Smart Run", self
            )  # not used in main gui
            smart_run_action.setIcon(self.icon_play)  # not used in main gui
            self.stop_run_action = QAction("Stop", self)
            self.stop_run_action.setIcon(self.icon_stop)

            menu.addAction(run_action)
            menu.addAction(run_until_menu_action)

        # Set the menu as the run button's dropdown menu
        self.btn_stop.setMenu(menu)
        self.btn_stop.setDefaultAction(run_action)
        self.btn_stop.setPopupMode(QToolButton.MenuButtonPopup)
        self.btn_stop.setDisabled(False)
        run_action.setToolTip("Run")

        # Config button
        self.btn_config = btn_config = create_button("tools.png", "Configure run")
        btn_config.hide()

        # Docs Window
        self.window_docs = BadgerDocsWindow(self, "")

        hbox_bg.addWidget(self.btn_del)
        # hbox_action.addWidget(btn_edit)
        hbox_bg.addWidget(self.btn_log)
        hbox_bg.addWidget(self.btn_help)
        hbox_bg.addStretch(1)
        hbox_bg.addWidget(self.btn_reset)
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

    def config_logic(self) -> None:
        self.btn_del.clicked.connect(self.delete_run)
        self.btn_log.clicked.connect(self.logbook)
        self.btn_help.clicked.connect(self.open_docs)
        self.btn_reset.clicked.connect(self.reset_env)
        self.btn_opt.clicked.connect(self.jump_to_optimal)
        self.btn_set.clicked.connect(self.dial_in)
        self.run_action.triggered.connect(self._on_run_action_triggered)
        self.run_until_action.triggered.connect(self._on_run_until_action_triggered)
        self.run_until_menu_action.triggered.connect(
            self._on_run_until_menu_action_triggered
        )
        self.smart_run_action.triggered.connect(self._on_smart_run_action_triggered)
        self.stop_run_action.triggered.connect(lambda: self.sig_stop.emit())
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

    def lock(self) -> None:
        self.btn_del.setDisabled(True)
        self.btn_log.setDisabled(True)
        self.btn_reset.setDisabled(True)
        self.btn_checkpoint.setDisabled(True)
        self.btn_stop.setDisabled(True)
        self.btn_opt.setDisabled(True)
        self.btn_set.setDisabled(True)

    def unlock(self) -> None:
        self.btn_del.setDisabled(False)
        self.btn_log.setDisabled(False)
        self.btn_reset.setDisabled(False)
        self.btn_checkpoint.setDisabled(False)
        self.btn_stop.setDisabled(False)
        self.btn_opt.setDisabled(False)
        self.btn_set.setDisabled(False)

    def routine_invalid(self) -> None:
        self.btn_stop.setDisabled(False)

    def routine_finished(self) -> None:
        # Note the order of the following two lines cannot be changed!
        self.btn_stop.setPopupMode(QToolButton.MenuButtonPopup)
        self.btn_stop.setStyleSheet(stylesheet_run)
        self.run_action.setText("New Run")
        self.run_action.setIcon(self.icon_play)
        self.run_until_menu_action.setIcon(self.icon_play_time)
        self.smart_run_action.setIcon(self.icon_play)
        self.run_until_menu_action.setText("Run until")
        self.smart_run_action.setText("Run")
        self.btn_stop.show_text()
        self.btn_stop.setDisabled(False)
        self.update_stop_menu(True)

        self.btn_reset.setDisabled(False)
        self.btn_set.setDisabled(False)
        self.btn_del.setDisabled(False)

    def toggle_reset(self, locked: bool) -> None:
        self.btn_reset.setDisabled(locked)

    def toggle_run(self, locked: bool) -> None:
        self.btn_stop.setDisabled(locked)

    def toggle_other(self, locked: bool) -> None:
        self.btn_del.setDisabled(locked)
        self.btn_log.setDisabled(locked)
        self.btn_opt.setDisabled(locked)
        self.btn_set.setDisabled(locked)

    def run_start(self) -> None:
        self.btn_stop.setStyleSheet(stylesheet_stop)
        # self.btn_stop.setPopupMode(QToolButton.DelayedPopup)
        self.btn_stop.setDisabled(False)
        self.run_action.setText("Stop")
        self.run_action.setIcon(self.icon_stop)
        self.run_until_action.setText("Stop")
        self.run_until_action.setIcon(self.icon_stop)
        self.run_until_menu_action.setText("Stop")
        self.run_until_menu_action.setIcon(self.icon_stop)
        self.smart_run_action.setText("Pause")
        self.smart_run_action.setIcon(self.icon_pause)
        self.btn_checkpoint.setDisabled(False)
        self.btn_set.setDisabled(True)
        self.update_stop_menu(False)

    def set_run_action(self) -> None:
        if self.mini_mode:
            # run action "New Run" sets flag to restart in run_controller
            self.sig_flag_restart.emit()
            self.sig_smart_run_ctrl.emit()
        else:
            if self.btn_stop.defaultAction() is not self.run_action:
                self.btn_stop.setDefaultAction(self.run_action)

            if self.run_action.text() == "Stop":
                self.btn_stop.setDisabled(True)
                self.sig_stop.emit()
            else:
                self.btn_stop.setDisabled(True)
                self.sig_start.emit()

    def set_run_until_action(self, from_menu=False):
        self.sig_update_tc.emit()

    def set_smart_run_action(self):
        if self.btn_stop.defaultAction() is not self.smart_run_action:
            self.btn_stop.setDefaultAction(self.smart_run_action)

        self.sig_smart_run_ctrl.emit()

    def _on_run_action_triggered(self) -> None:
        self.set_run_action()

    def _on_run_until_action_triggered(self):
        self.set_run_until_action(from_menu=False)

    def _on_run_until_menu_action_triggered(self):
        self.set_run_until_action(from_menu=True)

    def _on_smart_run_action_triggered(self) -> None:
        self.set_smart_run_action()

    def delete_run(self) -> None:
        self.sig_delete_run.emit()

    def logbook(self) -> None:
        self.sig_logbook.emit()

    def open_docs(self) -> None:
        self.window_docs.update_docs(self.docs_name)
        self.window_docs.show()

    def reset_env(self) -> None:
        self.sig_reset_env.emit()

    def jump_to_optimal(self) -> None:
        self.sig_jump_to_optimal.emit()

    def dial_in(self) -> None:
        self.sig_dial_in.emit()

    def handle_pause_action(self, status: bool) -> None:
        """
        Enable/disable buttons for pause (true)/resume (false) optimization
        """
        if status:
            # paused
            self.btn_stop.setStyleSheet(stylesheet_run)
            self.smart_run_action.setIcon(self.icon_play)
            self.run_until_menu_action.setIcon(self.icon_play_time)
            self.btn_stop.setDisabled(False)
            self.btn_reset.setDisabled(False)
            self.btn_set.setDisabled(False)
            self.btn_del.setDisabled(False)

        else:
            # running
            self.btn_stop.setStyleSheet(stylesheet_stop)
            self.smart_run_action.setIcon(self.icon_pause)
            self.btn_stop.setDisabled(False)
            self.btn_checkpoint.setDisabled(False)
            self.btn_set.setDisabled(True)
            self.btn_reset.setDisabled(True)

        self.update_stop_menu(status)

    def update_stop_menu(self, status: bool) -> None:
        """Update run menu options when routine is paused (true)/running (false)"""
        if status:
            self.run_menu.clear()
            self.run_action.setText("New Run")
            self.run_action.setIcon(self.icon_play)
            if self.mini_mode:
                self.run_until_menu_action.setText("Edit Condition")
            else:
                self.run_until_menu_action.setText("Run until")
            self.smart_run_action.setText("Run")
            self.run_menu.addAction(self.run_action)
            self.run_menu.addAction(self.run_until_menu_action)
            self.btn_stop.show_text()
        else:
            self.run_menu.clear()
            self.run_menu.addAction(self.stop_run_action)
            if self.mini_mode:
                self.run_menu.addAction(self.smart_run_action)
            self.btn_stop.hide_text()

    def open_extensions_palette(self) -> None:
        self.sig_open_extensions_palette.emit()

    def env_ready(self) -> None:
        self.btn_log.setDisabled(False)
        self.btn_opt.setDisabled(False)

    def update_run_tooltip(self, tc: dict[str, int | float] | None = None) -> None:
        """Update btn_stop tooltip with next termination condition"""
        tc_text = ""
        if tc is None:
            self.run_action.setToolTip("Run")
        else:
            tc_idx = tc.get("tc_idx", 0)
            if tc_idx == 0:
                tc_text = tc.get("max_eval", "")
                tip = f"Run until: n iterations = {tc_text}"
                tc_text = f"+{tc.get('max_eval', '')}"
            elif tc_idx == 1:
                tc_text = f"{int(tc.get('max_time', 0))} s"
                tip = f"Run until: timeout = {tc_text}"
            self.run_until_action.setToolTip(tip)
            self.run_until_menu_action.setToolTip(tip)

        self.update_run_button_text(str(tc_text))

    def update_run_button_text(self, text: str) -> None:
        self.btn_stop.setDisplayText(text)
