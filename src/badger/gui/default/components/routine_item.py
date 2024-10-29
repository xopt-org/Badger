from datetime import datetime
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel
from PyQt5.QtWidgets import QSizePolicy, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from badger.gui.default.components.eliding_label import ElidingLabel
from badger.gui.default.utils import create_button

stylesheet_normal_default = """
    background-color: #4C566A;
    border-radius: 2px;
"""

stylesheet_normal_hover_default = """
    background-color: #5E81AC;
    border-radius: 2px;
"""

stylesheet_activate_default = """
    background-color: #4B6789;
    border-radius: 2px;
"""

stylesheet_activate_hover_default = """
    background-color: #54749A;
    border-radius: 2px;
"""

stylesheet_del = """
QPushButton:hover:pressed
{
    background-color: #BF616A;
}
QPushButton:hover
{
    background-color: #A9444E;
}
QPushButton
{
    background-color: none;
    border-top-left-radius: 0px;
    border-bottom-left-radius: 0px;
}
"""

stylesheet_fav = """
QPushButton:hover:pressed
{
    background-color: #FFEA00;
}
QPushButton:hover
{
    background-color: #FFD600;
}
QPushButton
{
    background-color: none;
    border-radius: 0px;
}
"""


class BadgerRoutineItem(QWidget):
    # sig_del carries an id
    sig_del = pyqtSignal(str)

    def __init__(
        self, id, name, timestamp, environment, env_dict, description="", parent=None
    ):
        super().__init__(parent)

        self.activated = False
        self.hover = False
        self.id = id
        self.name = name
        self.timestamp = timestamp
        self.description = description
        if environment in env_dict:
            self.color_dict = env_dict[environment]
            self.stylesheet_normal = f"""
                background-color: {self.color_dict['normal']};
                border-radius: 2px;
            """
            self.stylesheet_normal_hover = f"""
                background-color: {self.color_dict['normal_hover']};
                border-radius: 2px;
            """
            self.stylesheet_activate = f"""
                background-color: {self.color_dict['activate']};
                border-radius: 2px;
            """
            self.stylesheet_activate_hover = f"""
                background-color: {self.color_dict['activate_hover']};
                border-radius: 2px;
            """
        else:
            self.stylesheet_normal = stylesheet_normal_default
            self.stylesheet_normal_hover = stylesheet_normal_hover_default
            self.stylesheet_activate = stylesheet_activate_default
            self.stylesheet_activate_hover = stylesheet_activate_hover_default

        self.init_ui()
        self.config_logic()

    def init_ui(self):
        self.setAttribute(Qt.WA_StyledBackground)
        self.setStyleSheet(self.stylesheet_normal)

        cool_font = QFont()
        cool_font.setWeight(QFont.DemiBold)
        cool_font.setPixelSize(16)

        hbox = QHBoxLayout(self)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(0)
        info_panel = QWidget()
        hbox.addWidget(info_panel, 1)
        vbox = QVBoxLayout(info_panel)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(0)
        name_panel = QWidget()
        hbox_name = QHBoxLayout(name_panel)
        hbox_name.setContentsMargins(4, 0, 0, 0)
        routine_name = ElidingLabel(self.name)
        routine_name.setMinimumWidth(180)
        routine_name.setFont(cool_font)
        hbox_name.addWidget(routine_name)
        vbox.addWidget(name_panel)
        _timestamp = datetime.fromisoformat(self.timestamp)
        time_str = _timestamp.strftime("%m/%d/%Y, %H:%M:%S")
        time_created = QLabel(time_str)
        vbox.addWidget(time_created)

        # Routine tools
        self.btn_fav = btn_fav = create_button(
            "star.png", "Favorite routine", stylesheet_fav, size=None
        )
        btn_fav.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        btn_fav.setFixedWidth(32)
        btn_fav.hide()  # hide it for now
        self.btn_del = btn_del = create_button(
            "trash.png", "Delete routine", stylesheet_del, size=None
        )
        btn_del.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        btn_del.setFixedWidth(32)
        # btn_del.hide()
        hbox.addWidget(btn_fav)
        hbox.addWidget(btn_del)

        self.update_tooltip()

    def config_logic(self):
        self.btn_del.clicked.connect(self.delete_routine)
        # self.btn_fav.clicked.connect(self.favorite_routine)

    def activate(self):
        self.activated = True
        if self.hover:
            self.setStyleSheet(self.stylesheet_activate_hover)
        else:
            self.setStyleSheet(self.stylesheet_activate)

    def deactivate(self):
        self.activated = False
        if self.hover:
            self.setStyleSheet(self.stylesheet_normal_hover)
        else:
            self.setStyleSheet(self.stylesheet_normal)

    def enterEvent(self, event):
        self.hover = True
        # self.btn_fav.show()
        # self.btn_del.show()
        if self.activated:
            self.setStyleSheet(self.stylesheet_activate_hover)
        else:
            self.setStyleSheet(self.stylesheet_normal_hover)

    def leaveEvent(self, event):
        self.hover = False
        # self.btn_fav.hide()
        # self.btn_del.hide()
        if self.activated:
            self.setStyleSheet(self.stylesheet_activate)
        else:
            self.setStyleSheet(self.stylesheet_normal)

    def delete_routine(self):
        reply = QMessageBox.question(
            self.parent(),
            "Delete routine",
            f"Are you sure you want to delete routine {self.name}?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self.sig_del.emit(self.id)

    def update_tooltip(self):
        _timestamp = datetime.fromisoformat(self.timestamp)
        time_str = _timestamp.strftime("%m/%d/%Y, %H:%M:%S")
        self.setToolTip(
            f"name: {self.name}\ncreated at: {time_str}\ndescription:\n{self.description}"
        )

    def update_description(self, descr):
        self.description = descr
        self.update_tooltip()
