from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QPlainTextEdit,
    QLineEdit,
)
from PyQt5.QtWidgets import (
    QCheckBox,
    QStyledItemDelegate,
    QLabel,
    QListWidget,
    QFrame,
)
from PyQt5.QtCore import QRegExp

from badger.gui.default.components.collapsible_box import CollapsibleBox
from badger.gui.default.components.var_table import VariableTable
from badger.gui.default.components.obj_table import ObjectiveTable
from badger.gui.default.components.data_table import init_data_table
from badger.settings import init_settings
from badger.gui.default.utils import (
    MouseWheelWidgetAdjustmentGuard,
    NoHoverFocusComboBox,
)
from badger.utils import strtobool

LABEL_WIDTH = 80

stylesheet_auto = """
    #VarPanel {
        border: 4px solid #FDD835;
        border-radius: 4px;
    }
"""

stylesheet_auto_msg = """
    QLabel {
        background-color: #FDD835;
        color: #19232D;
        padding: 4px 4px 8px 4px;
        border-radius: 0;
    }
"""


class BadgerEnvBox(CollapsibleBox):
    def __init__(self, env_dict, parent=None, envs=[]):
        super().__init__(parent, " Environment + VOCS")

        self.envs = envs
        self.env_dict = env_dict

        self.init_ui()
        self.config_logic()

    def init_ui(self):
        config_singleton = init_settings()
        vbox = QVBoxLayout()

        self.content_area.setObjectName("EnvBox")

        name = QWidget()
        hbox_name = QHBoxLayout(name)
        hbox_name.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Name")
        lbl.setFixedWidth(LABEL_WIDTH)
        self.cb = cb = NoHoverFocusComboBox()
        cb.setItemDelegate(QStyledItemDelegate())
        cb.addItems(self.envs)
        cb.setCurrentIndex(-1)
        cb.installEventFilter(MouseWheelWidgetAdjustmentGuard(cb))
        self.btn_env_play = btn_env_play = QPushButton("Open Playground")
        btn_env_play.setFixedSize(128, 24)
        if not strtobool(config_singleton.read_value("BADGER_ENABLE_ADVANCED")):
            btn_env_play.hide()
        self.btn_docs = btn_docs = QPushButton("Open Docs")
        btn_docs.setFixedSize(128, 24)
        hbox_name.addWidget(lbl)
        hbox_name.addWidget(cb, 1)
        hbox_name.addWidget(btn_env_play)
        hbox_name.addWidget(btn_docs)
        vbox.addWidget(name)

        params = QWidget()
        hbox_params = QHBoxLayout(params)
        hbox_params.setContentsMargins(0, 0, 0, 0)
        lbl_params_col = QWidget()
        vbox_lbl_params = QVBoxLayout(lbl_params_col)
        vbox_lbl_params.setContentsMargins(0, 0, 0, 0)
        lbl_params = QLabel("Params")
        lbl_params.setFixedWidth(LABEL_WIDTH)
        vbox_lbl_params.addWidget(lbl_params)
        vbox_lbl_params.addStretch(1)
        hbox_params.addWidget(lbl_params_col)

        edit_params_col = QWidget()
        vbox_params_edit = QVBoxLayout(edit_params_col)
        vbox_params_edit.setContentsMargins(0, 0, 0, 0)
        self.edit = edit = QPlainTextEdit()
        # edit.setMaximumHeight(80)
        edit.setMinimumHeight(480)
        vbox_params_edit.addWidget(edit)
        hbox_params.addWidget(edit_params_col)
        vbox.addWidget(params)

        seperator = QFrame()
        seperator.setFrameShape(QFrame.HLine)
        seperator.setFrameShadow(QFrame.Sunken)
        seperator.setLineWidth(0)
        seperator.setMidLineWidth(0)
        vbox.addWidget(seperator)

        # Variables config (table style)
        self.var_panel = var_panel = QWidget()
        var_panel.setObjectName("VarPanel")
        var_panel.setMinimumHeight(280)
        vbox.addWidget(var_panel, 2)
        self.vbox_var = vbox_var = QVBoxLayout(var_panel)
        vbox_var.setContentsMargins(4, 4, 4, 4)
        vbox_var.setSpacing(0)
        msg_auto = QLabel(
            "The values you see in the variable ranges spin "
            "boxes and initial points table are preview that "
            "generated either based on current machine state, "
            "or the machine state at the time of this historical"
            " run. The real values would be regenerated based on"
            " the machine state before running the optimization "
            "again."
        )
        if not config_singleton.read_value("AUTO_REFRESH"):
            msg_auto = QLabel(
                "Auto mode is on.  To explicitly set the "
                "variable ranges and/or initial points,  please "
                'uncheck the "Automatic" check box.'
            )
        msg_auto.setWordWrap(True)
        msg_auto.setStyleSheet(stylesheet_auto_msg)
        msg_auto.hide()
        self.msg_auto = msg_auto
        vbox_var.addWidget(msg_auto)
        var_panel_origin = QWidget()
        vbox_var.addWidget(var_panel_origin)
        self.hbox_var = hbox_var = QHBoxLayout(var_panel_origin)
        lbl_var_col = QWidget()
        vbox_lbl_var = QVBoxLayout(lbl_var_col)
        vbox_lbl_var.setContentsMargins(0, 0, 0, 0)
        lbl_var = QLabel("Variables")
        lbl_var.setFixedWidth(LABEL_WIDTH)
        vbox_lbl_var.addWidget(lbl_var)
        vbox_lbl_var.addStretch(1)
        hbox_var.addWidget(lbl_var_col)

        edit_var_col = QWidget()
        vbox_var_edit = QVBoxLayout(edit_var_col)
        vbox_var_edit.setContentsMargins(0, 0, 0, 0)

        # Add relative to current option
        action_common = QWidget()
        hbox_action_common = QHBoxLayout(action_common)
        hbox_action_common.setContentsMargins(0, 0, 0, 0)
        vbox_var_edit.addWidget(action_common)
        self.relative_to_curr = relative_to_curr = QCheckBox("Automatic")
        relative_to_curr.setChecked(True)
        tooltip = (
            "If checked, you will not be able to change the\n"
            + "variable ranges and initial points manually.\n"
            + "Instead, the variable ranges and the initial points will be\n"
            + "generated based on the current state.\n\n"
            + 'You can adjust them by using the "Set Variable Range"\n'
            + 'button and the "Add Current"/"Add Random" buttons.\n'
            + "The actual values of those settings will be re-calculated\n"
            + "based on the machine state at the time of running."
        )
        relative_to_curr.setToolTip(tooltip)
        hbox_action_common.addWidget(relative_to_curr)
        hbox_action_common.addStretch()

        action_var = QWidget()
        hbox_action_var = QHBoxLayout(action_var)
        hbox_action_var.setContentsMargins(0, 0, 0, 0)
        vbox_var_edit.addWidget(action_var)
        self.edit_var = edit_var = QLineEdit()
        edit_var.setPlaceholderText("Filter variables...")
        edit_var.setFixedWidth(160)
        self.btn_add_var = btn_add_var = QPushButton("Add")
        btn_add_var.setFixedSize(96, 24)
        btn_add_var.setDisabled(True)
        if not strtobool(config_singleton.read_value("BADGER_ENABLE_ADVANCED")):
            btn_add_var.hide()
        self.btn_lim_vrange = btn_lim_vrange = QPushButton("Set Variable Range")
        btn_lim_vrange.setFixedSize(144, 24)
        btn_lim_vrange.setDisabled(True)
        self.check_only_var = check_only_var = QCheckBox("Show Checked Only")
        check_only_var.setChecked(False)
        hbox_action_var.addWidget(edit_var)
        hbox_action_var.addWidget(btn_add_var)
        hbox_action_var.addWidget(btn_lim_vrange)
        hbox_action_var.addStretch()
        hbox_action_var.addWidget(check_only_var)

        self.var_table = VariableTable()
        self.var_table.lock_bounds()
        vbox_var_edit.addWidget(self.var_table)

        cbox_init = CollapsibleBox(
            self,
            " Initial Points",
            tooltip="If set, it takes precedence over the start from current setting in generator configuration.",
        )
        vbox_var_edit.addWidget(cbox_init)
        vbox_init = QVBoxLayout()
        vbox_init.setContentsMargins(8, 8, 8, 8)
        action_init = QWidget()
        hbox_action_init = QHBoxLayout(action_init)
        hbox_action_init.setContentsMargins(0, 0, 0, 0)
        self.btn_add_row = btn_add_row = QPushButton("Add Row")
        btn_add_row.setFixedSize(96, 24)
        self.btn_add_curr = btn_add_curr = QPushButton("Add Current")
        btn_add_curr.setFixedSize(96, 24)
        self.btn_add_rand = btn_add_rand = QPushButton("Add Random")
        btn_add_rand.setFixedSize(96, 24)
        self.btn_clear = btn_clear = QPushButton("Clear All")
        btn_clear.setFixedSize(96, 24)
        hbox_action_init.addWidget(btn_add_row)
        hbox_action_init.addStretch()
        hbox_action_init.addWidget(btn_add_curr)
        hbox_action_init.addWidget(btn_add_rand)
        hbox_action_init.addWidget(btn_clear)
        vbox_init.addWidget(action_init)
        self.init_table = init_data_table()
        self.init_table.set_uneditable()
        vbox_init.addWidget(self.init_table)
        cbox_init.setContentLayout(vbox_init)
        cbox_init.expand()

        hbox_var.addWidget(edit_var_col)

        # Objectives config (table style)
        obj_panel = QWidget()
        vbox.addWidget(obj_panel, 1)
        hbox_obj = QHBoxLayout(obj_panel)
        hbox_obj.setContentsMargins(0, 0, 0, 0)
        lbl_obj_col = QWidget()
        vbox_lbl_obj = QVBoxLayout(lbl_obj_col)
        vbox_lbl_obj.setContentsMargins(0, 0, 0, 0)
        lbl_obj = QLabel("Objectives")
        lbl_obj.setFixedWidth(LABEL_WIDTH)
        vbox_lbl_obj.addWidget(lbl_obj)
        vbox_lbl_obj.addStretch(1)
        hbox_obj.addWidget(lbl_obj_col)

        edit_obj_col = QWidget()
        vbox_obj_edit = QVBoxLayout(edit_obj_col)
        vbox_obj_edit.setContentsMargins(0, 0, 0, 0)

        action_obj = QWidget()
        hbox_action_obj = QHBoxLayout(action_obj)
        hbox_action_obj.setContentsMargins(0, 0, 0, 0)
        vbox_obj_edit.addWidget(action_obj)
        self.edit_obj = edit_obj = QLineEdit()
        edit_obj.setPlaceholderText("Filter objectives...")
        edit_obj.setFixedWidth(192)
        self.check_only_obj = check_only_obj = QCheckBox("Show Checked Only")
        check_only_obj.setChecked(False)
        hbox_action_obj.addWidget(edit_obj)
        hbox_action_obj.addStretch()
        hbox_action_obj.addWidget(check_only_obj)

        self.obj_table = ObjectiveTable()
        vbox_obj_edit.addWidget(self.obj_table)
        hbox_obj.addWidget(edit_obj_col)

        cbox_more = CollapsibleBox(self, " More")
        vbox.addWidget(cbox_more)
        vbox_more = QVBoxLayout()

        # Constraints config
        con_panel = QWidget()
        vbox_more.addWidget(con_panel, 1)
        hbox_con = QHBoxLayout(con_panel)
        hbox_con.setContentsMargins(0, 0, 0, 0)
        lbl_con_col = QWidget()
        vbox_lbl_con = QVBoxLayout(lbl_con_col)
        vbox_lbl_con.setContentsMargins(0, 0, 0, 0)
        lbl_con = QLabel("Constraints")
        lbl_con.setFixedWidth(LABEL_WIDTH)
        vbox_lbl_con.addWidget(lbl_con)
        vbox_lbl_con.addStretch(1)
        hbox_con.addWidget(lbl_con_col)

        edit_con_col = QWidget()
        vbox_con_edit = QVBoxLayout(edit_con_col)
        vbox_con_edit.setContentsMargins(0, 0, 0, 0)
        action_con = QWidget()
        hbox_action_con = QHBoxLayout(action_con)
        hbox_action_con.setContentsMargins(0, 0, 0, 0)
        vbox_con_edit.addWidget(action_con)
        self.btn_add_con = btn_add_con = QPushButton("Add")
        btn_add_con.setFixedSize(96, 24)
        btn_add_con.setDisabled(True)
        hbox_action_con.addWidget(btn_add_con)
        hbox_action_con.addStretch()
        self.list_con = QListWidget()
        self.list_con.setMaximumHeight(80)
        # self.list_con.setFixedHeight(64)
        self.list_con.setViewportMargins(2, 2, 17, 2)
        vbox_con_edit.addWidget(self.list_con)
        # vbox_con_edit.addStretch()
        hbox_con.addWidget(edit_con_col)

        # States config
        sta_panel = QWidget()
        vbox_more.addWidget(sta_panel, 1)
        hbox_sta = QHBoxLayout(sta_panel)
        hbox_sta.setContentsMargins(0, 0, 0, 0)
        lbl_sta_col = QWidget()
        vbox_lbl_sta = QVBoxLayout(lbl_sta_col)
        vbox_lbl_sta.setContentsMargins(0, 0, 0, 0)
        lbl_sta = QLabel("Observables")
        lbl_sta.setFixedWidth(LABEL_WIDTH)
        vbox_lbl_sta.addWidget(lbl_sta)
        vbox_lbl_sta.addStretch(1)
        hbox_sta.addWidget(lbl_sta_col)

        edit_sta_col = QWidget()
        vbox_sta_edit = QVBoxLayout(edit_sta_col)
        vbox_sta_edit.setContentsMargins(0, 0, 0, 0)
        action_sta = QWidget()
        hbox_action_sta = QHBoxLayout(action_sta)
        hbox_action_sta.setContentsMargins(0, 0, 0, 0)
        vbox_sta_edit.addWidget(action_sta)
        self.btn_add_sta = btn_add_sta = QPushButton("Add")
        btn_add_sta.setFixedSize(96, 24)
        btn_add_sta.setDisabled(True)
        hbox_action_sta.addWidget(btn_add_sta)
        hbox_action_sta.addStretch()
        self.list_obs = QListWidget()
        self.list_obs.setMaximumHeight(80)
        # self.list_obs.setFixedHeight(64)
        self.list_obs.setViewportMargins(2, 2, 17, 2)
        vbox_sta_edit.addWidget(self.list_obs)
        # vbox_sta_edit.addStretch()
        hbox_sta.addWidget(edit_sta_col)
        cbox_more.setContentLayout(vbox_more)

        self.setContentLayout(vbox)

    def config_logic(self):
        self.dict_con = {}

        self.edit_var.textChanged.connect(self.filter_var)
        self.check_only_var.stateChanged.connect(self.toggle_var_show_mode)
        self.edit_obj.textChanged.connect(self.filter_obj)
        self.check_only_obj.stateChanged.connect(self.toggle_obj_show_mode)

    def toggle_var_show_mode(self, _):
        self.var_table.toggle_show_mode(self.check_only_var.isChecked())

    def add_var(self, name, lb, ub):
        self.var_table.add_variable(name, lb, ub)
        self.filter_var()

    def filter_var(self):
        keyword = self.edit_var.text()
        rx = QRegExp(keyword)

        _variables = []
        for var in self.var_table.all_variables:
            vname = next(iter(var))
            if rx.indexIn(vname, 0) != -1:
                _variables.append(var)

        self.var_table.update_variables(_variables, 1)

    def toggle_obj_show_mode(self, _):
        self.obj_table.toggle_show_mode(self.check_only_obj.isChecked())

    def filter_obj(self):
        keyword = self.edit_obj.text()
        rx = QRegExp(keyword)

        _objectives = []
        for obj in self.obj_table.all_objectives:
            oname = next(iter(obj))
            if rx.indexIn(oname, 0) != -1:
                _objectives.append(obj)

        self.obj_table.update_objectives(_objectives, 1)

    def _fit_content(self, list):
        height = list.sizeHintForRow(0) * list.count() + 2 * list.frameWidth() + 4
        height = max(28, min(height, 192))
        list.setFixedHeight(height)

    def fit_content(self):
        return
        self._fit_content(self.list_obj)
        self._fit_content(self.list_con)
        self._fit_content(self.list_obs)

    def switch_var_panel_style(self, auto=True):
        if auto:
            self.var_panel.setStyleSheet(stylesheet_auto)
            self.vbox_var.setContentsMargins(4, 4, 4, 4)
            self.hbox_var.setContentsMargins(8, 8, 8, 8)
            self.msg_auto.show()
        else:
            self.var_panel.setStyleSheet(None)
            self.vbox_var.setContentsMargins(0, 0, 0, 0)
            self.hbox_var.setContentsMargins(0, 0, 0, 0)
            self.msg_auto.hide()

    def update_stylesheets(self, environment=""):
        if environment in self.env_dict:
            color_dict = self.env_dict[environment]
            stylesheet = f"""
                #EnvBox {{
                    border-radius: 4px;
                    border-color: {color_dict['normal']};
                    border-width: 4px;
                }}
            """
        else:
            stylesheet = ""
        self.setStyleSheet(stylesheet)
