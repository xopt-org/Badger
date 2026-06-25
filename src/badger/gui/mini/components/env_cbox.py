"""
Composite editor panel for configuring a Badger optimization routine.

Combines environment selection, algorithm selection, and all VOCS editors
(variables, objectives, constraints, observables) into a single widget.
Template loading populates every sub-table at once; individual changes in
vocs tables emit ``vocs_updated`` so the rest of the UI stays in sync.
"""

from pathlib import Path
from typing import Any

from PyQt5.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QStyle,
    QStyleOptionComboBox,
    QWidget,
    QLineEdit,
    QTreeWidget,
)
from PyQt5.QtWidgets import (
    QCheckBox,
    QStyledItemDelegate,
    QLabel,
)
from PyQt5.QtCore import QRegExp, pyqtSignal
from badger.gui.components.obs_table import ObservableTable
from badger.settings import init_settings
from pydantic_core import ValidationError

from badger.errors import BadgerRoutineError
from badger.gui.components.collapsible_box import CollapsibleBox
from badger.gui.components.pydantic_editor import BadgerPydanticEditor
from badger.gui.mini.components.var_table import VariableTable
from badger.gui.components.obj_table import ObjectiveTable
from badger.gui.components.con_table import ConstraintTable
from badger.gui.components.data_table import init_data_table
from badger.gui.utils import (
    MouseWheelWidgetAdjustmentGuard,
    NoHoverFocusComboBox,
)
from xopt.vocs import VOCS
from gest_api.vocs import ContinuousVariable

import logging

LABEL_WIDTH = 96


CONS_RELATION_DICT = {
    ">": "GREATER_THAN",
    "<": "LESS_THAN",
}


logger = logging.getLogger(__name__)


class ArrowOnlyPopupComboBox(NoHoverFocusComboBox):
    """Open popup only when the dropdown arrow is clicked."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setStyleSheet(
            """
            QComboBox {
                color: darkGray;
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QComboBox::drop-down {
                border: none;
                width: 14px;
            }
            """
        )
        self.setItemDelegate(QStyledItemDelegate())
        self.installEventFilter(MouseWheelWidgetAdjustmentGuard(self))

    def mousePressEvent(self, event):
        option = QStyleOptionComboBox()
        self.initStyleOption(option)
        arrow_rect = self.style().subControlRect(
            QStyle.CC_ComboBox,
            option,
            QStyle.SC_ComboBoxArrow,
            self,
        )

        if arrow_rect.contains(event.pos()):
            super().mousePressEvent(event)
            return

        event.ignore()


def format_validation_error(e: ValidationError) -> str:
    """Convert Pydantic ValidationError into a friendly message."""
    messages = ["\n"]
    for err in e.errors():
        loc = " -> ".join(str(item) for item in err["loc"])
        msg = f"{loc}: {err['msg']}\n"
        messages.append(msg)
    return "\n".join(messages)


class TemplateSelectorRow(QFrame):
    """
    Row widget for template selection in the routine editor.
    This class contains specific stylesheets to make the template row
    stand out on the GUI.
    """

    def __init__(self, label_width: int, parent: QWidget | None = None):
        super().__init__(parent)

        self.setObjectName("TemplateSelectorRow")

        self.unselected_stylesheet = """
            QFrame#TemplateSelectorRow {
                background-color: #4E6788;
                border: 1px solid #96B5D8;
                border-radius: 10px;
            }
            QLabel#TemplateSelectorLabel {
                background-color: transparent;
                border: none;
                color: #EEF6FF;
                font-weight: 700;
            }
            QComboBox#TemplateSelectorCombo {
                background-color: #2A3748;
                color: #E6EEFA;
                border: 1px solid #89A6CA;
                selection-background-color: #6F95C5;
                selection-color: #F6FAFF;
            }
            QPushButton#TemplateSelectorButton {
                border: 1px solid #8CA5C4;
                border-radius: 4px;
            }
            QPushButton#TemplateSelectorButton:hover {
                border: 1px solid #A9C3E6;
            }
            QPushButton#TemplateSelectorButton:hover:pressed {
                border: 1px solid #C0DDFF;
            }
        """

        self.selected_stylesheet = """
            QFrame#TemplateSelectorRow {
                background-color: #3D4754;
                border: 1px solid #96B5D8;
                border-radius: 10px;
            }
            QLabel#TemplateSelectorLabel {
                background-color: transparent;
                border: none;
                color: #EEF6FF;
                font-weight: 700;
            }
            QComboBox#TemplateSelectorCombo {
                background-color: #2A3748;
                color: #E6EEFA;
                border: 1px solid #89A6CA;
                selection-background-color: #6F95C5;
                selection-color: #F6FAFF;
            }
            QPushButton#TemplateSelectorButton {
                border: 1px solid #8CA5C4;
                border-radius: 4px;
            }
            QPushButton#TemplateSelectorButton:hover {
                border: 1px solid #A9C3E6;
            }
            QPushButton#TemplateSelectorButton:hover:pressed {
                border: 1px solid #C0DDFF;
            }
        """

        self.setStyleSheet(self.unselected_stylesheet)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(0)

        self.label = QLabel("Template")
        self.label.setObjectName("TemplateSelectorLabel")
        self.label.setFixedWidth(label_width)

        self.template_cb = NoHoverFocusComboBox()
        self.template_cb.setObjectName("TemplateSelectorCombo")
        self.template_cb.setFixedWidth(label_width * 2)
        self.template_cb.setItemDelegate(QStyledItemDelegate())
        self.template_cb.setCurrentIndex(-1)
        self.template_cb.installEventFilter(
            MouseWheelWidgetAdjustmentGuard(self.template_cb)
        )

        self.load_template_button = QPushButton("From file")
        self.load_template_button.setObjectName("TemplateSelectorButton")
        self.load_template_button.setFixedSize(96, 24)
        self.load_template_button.setFixedHeight(24)

        layout.addWidget(self.label)
        layout.addSpacing(6)
        layout.addWidget(self.template_cb)
        layout.addSpacing(14)
        layout.addWidget(self.load_template_button)
        layout.addStretch()

        self.template_cb.currentIndexChanged.connect(self.sync_selection_state)
        self.sync_selection_state()

    def sync_selection_state(self):
        has_selection = self.template_cb.currentIndex() != -1
        self.setStyleSheet(
            self.selected_stylesheet if has_selection else self.unselected_stylesheet
        )
        self.update()


class BadgerEnvBox(QWidget):
    vocs_updated = pyqtSignal(object)  # or use a more specific type if you want

    def __init__(
        self,
        parent: QWidget | None = None,
        envs: list[str] = [],
        generators: list[str] = [],
    ):
        super().__init__(parent)

        self.envs = envs
        self.generators = generators

        # selected environment
        self.env_name = None

        self.init_ui()
        self.config_logic()

    def get_selected_env_name(self) -> str | None:
        """Return self.env_name"""
        return self.env_name

    def set_selected_env_name(self, env_name: str | None) -> None:
        """Set selected environment name and update UI accordingly."""
        self.env_name = env_name

        if env_name is None:
            self.env_cb.setCurrentIndex(-1)
            return

        idx = self.env_cb.findText(env_name)
        self.env_cb.setCurrentIndex(idx)

    def clear_selected_env(self) -> None:
        """Clear selected environment."""
        self.set_selected_env_name(None)

    def init_ui(self):
        self.setObjectName("EnvBox")

        # vbox layout
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(8, 8, 8, 8)
        vbox.setSpacing(8)

        self.template_row = TemplateSelectorRow(LABEL_WIDTH, self)
        self.template_cb = self.template_row.template_cb
        self.load_template_button = self.template_row.load_template_button

        config_singleton = init_settings()
        BADGER_PLUGIN_ROOT = config_singleton.read_value("BADGER_PLUGIN_ROOT")
        try:
            template_dir = Path(config_singleton.read_value("BADGER_TEMPLATE_ROOT"))
        except KeyError:
            template_dir = Path(BADGER_PLUGIN_ROOT) / "templates"
        yaml_files = list(template_dir.glob("*.y*ml"))
        self.template_cb.addItems([file.stem for file in sorted(yaml_files)])
        self.template_cb.setCurrentIndex(-1)

        vbox.addWidget(self.template_row)

        # Add a horizontal separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #61748c;")
        vbox.addWidget(separator)

        # Environment
        env = QWidget()
        vbox_env = QVBoxLayout(env)
        vbox_env.setContentsMargins(0, 0, 0, 0)
        select_env = QWidget()
        hbox_select_env = QHBoxLayout(select_env)
        hbox_select_env.setContentsMargins(0, 0, 0, 0)
        hbox_select_env.setSpacing(6)
        env_lbl = QLabel("Badger Environment:")  # label
        env_lbl.setFixedWidth(LABEL_WIDTH + 52)
        env_lbl.setStyleSheet("color: darkGray;")

        self.env_cb = env_cb = ArrowOnlyPopupComboBox()
        self.env_cb.setFixedWidth(LABEL_WIDTH + 44)
        env_cb.addItems(self.envs)
        env_cb.setCurrentIndex(-1)
        env_cb.setPlaceholderText("")

        self.btn_env_params = QPushButton("Parameters")  # params btn
        self.btn_env_params.setFixedSize(96, 24)
        self.btn_env_params.setCheckable(True)
        self.set_selected_env_name(None)

        self.btn_env_docs = QPushButton("Open Docs")
        self.btn_env_docs.setFixedSize(96, 24)
        self.btn_env_docs.setToolTip("Open environment docs")

        hbox_select_env.addWidget(env_lbl)
        hbox_select_env.addWidget(env_cb)
        hbox_select_env.addSpacing(8)
        hbox_select_env.addWidget(self.btn_env_params)
        hbox_select_env.addWidget(self.btn_env_docs)
        hbox_select_env.addStretch()

        # Environment params editor (hidden)
        self.edit_env_params = BadgerPydanticEditor()
        self.edit_env_params.hide()

        vbox_env.addWidget(select_env)
        vbox_env.addWidget(self.edit_env_params)

        vbox.addWidget(env)

        # Algorithm
        algo_widget = QWidget()
        hbox_algo = QHBoxLayout(algo_widget)
        hbox_algo.setContentsMargins(0, 0, 0, 0)
        hbox_algo.setSpacing(6)
        algo_lbl = QLabel("Algorithm")  # label
        algo_lbl.setFixedWidth(LABEL_WIDTH)
        self.algo_cb = algo_cb = NoHoverFocusComboBox()  # comboBox
        algo_cb.setFixedWidth(LABEL_WIDTH * 2)
        algo_cb.setItemDelegate(QStyledItemDelegate())
        algo_cb.addItems(self.generators)
        algo_cb.setCurrentIndex(-1)
        algo_cb.installEventFilter(MouseWheelWidgetAdjustmentGuard(algo_cb))
        self.btn_algo_parans = QPushButton("Parameters")
        self.btn_algo_parans.setFixedSize(96, 24)
        self.btn_algo_parans.setCheckable(True)

        self.btn_algo_docs = QPushButton("Open Docs")
        self.btn_algo_docs.setFixedSize(96, 24)
        self.btn_algo_docs.setToolTip("Open algorithm docs")

        hbox_algo.addWidget(algo_lbl)
        hbox_algo.addWidget(algo_cb)
        hbox_algo.addSpacing(8)
        hbox_algo.addWidget(self.btn_algo_parans)
        hbox_algo.addWidget(self.btn_algo_docs)
        hbox_algo.addStretch()

        self.edit_algo_params = BadgerPydanticEditor()
        self.edit_algo_params.hide()

        vbox.addWidget(algo_widget)
        vbox.addWidget(self.edit_algo_params)

        self.relative_to_curr = QCheckBox("Automatic")
        self.relative_to_curr.setChecked(True)
        self.relative_to_curr.hide()
        vbox.addWidget(self.relative_to_curr)

        # Variables
        var_panel_origin = QWidget()

        # construct variables as an hbox, with label, stretch, then table on the right
        hbox_var = QHBoxLayout(var_panel_origin)
        hbox_var.setContentsMargins(0, 0, 0, 0)
        hbox_var.setSpacing(6)

        lbl_var_col = QWidget()  # column with stretch under
        lbl_var_col.setFixedWidth(LABEL_WIDTH)
        vbox_lbl_var = QVBoxLayout(lbl_var_col)
        vbox_lbl_var.setContentsMargins(0, 0, 0, 0)
        lbl_var = QLabel("Variables")
        lbl_var.setFixedWidth(LABEL_WIDTH)
        vbox_lbl_var.addWidget(lbl_var)
        vbox_lbl_var.addStretch(1)
        hbox_var.addWidget(lbl_var_col)

        vbox.addWidget(var_panel_origin, 1)

        # Edit variables (right side of hbox_var)
        edit_var_col = QWidget()
        vbox_var_edit = QVBoxLayout(edit_var_col)
        vbox_var_edit.setContentsMargins(0, 2, 0, 2)
        vbox_var_edit.setSpacing(6)

        # variables menu bar
        action_var = QWidget()
        hbox_action_var = QHBoxLayout(action_var)
        hbox_action_var.setContentsMargins(0, 0, 0, 0)
        hbox_action_var.setSpacing(0)
        vbox_var_edit.addWidget(action_var)
        # filter variables
        self.edit_var = edit_var = QLineEdit()
        edit_var.setPlaceholderText("Filter variables...")
        edit_var.setFixedWidth(192)

        # refresh current
        self.refresh_current_btn = QPushButton("Refresh")
        self.refresh_current_btn.setFixedSize(96, 24)

        # show checked only
        self.check_only_var = check_only_var = QCheckBox("Show Checked Only")
        check_only_var.setChecked(False)
        hbox_action_var.addWidget(edit_var)
        hbox_action_var.addSpacing(14)
        hbox_action_var.addWidget(self.refresh_current_btn)
        hbox_action_var.addStretch()
        hbox_action_var.addWidget(check_only_var)

        # var table
        self.var_table = VariableTable()
        # self.var_table.lock_bounds()
        self.var_table.setMinimumHeight(240)
        self.var_table.verticalHeader().setVisible(False)
        vbox_var_edit.addWidget(self.var_table, 1)

        self.var_table.verticalHeader().setDefaultSectionSize(27)

        # Initial Points
        collapsiblebox_init = CollapsibleBox(
            self,
            " Initial Points",
        )
        collapsiblebox_init.toggle_button.setFixedHeight(24)
        vbox_var_edit.addWidget(collapsiblebox_init)
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
        collapsiblebox_init.setContentLayout(vbox_init)
        # cbox_init.expand()

        hbox_var.addWidget(edit_var_col)

        # Objectives config (table style)
        obj_panel = QWidget()
        vbox.addWidget(obj_panel)
        hbox_obj = QHBoxLayout(obj_panel)
        hbox_obj.setContentsMargins(0, 0, 0, 0)
        hbox_obj.setSpacing(6)
        lbl_obj_col = QWidget()
        lbl_obj_col.setFixedWidth(LABEL_WIDTH)
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
        self.obj_table.setMinimumHeight(120)
        vbox_obj_edit.addWidget(self.obj_table)
        hbox_obj.addWidget(edit_obj_col)

        cbox_more = CollapsibleBox(self, " Constraints + Observables")
        vbox.addWidget(cbox_more)
        vbox_more = QVBoxLayout()

        # Constraints config
        con_panel = QWidget()
        vbox_more.addWidget(con_panel)
        hbox_con = QHBoxLayout(con_panel)
        hbox_con.setContentsMargins(0, 0, 0, 0)
        hbox_con.setSpacing(6)
        lbl_con_col = QWidget()
        lbl_con_col.setFixedWidth(LABEL_WIDTH)
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
        self.edit_con = edit_con = QLineEdit()
        edit_con.setPlaceholderText("Filter constraints...")
        edit_con.setFixedWidth(192)
        self.check_only_con = check_only_con = QCheckBox("Show Checked Only")
        check_only_con.setChecked(False)
        hbox_action_con.addWidget(edit_con)
        hbox_action_con.addStretch()
        hbox_action_con.addWidget(check_only_con)

        self.con_table = ConstraintTable()
        self.con_table.setMinimumHeight(120)
        vbox_con_edit.addWidget(self.con_table)
        hbox_con.addWidget(edit_con_col)

        # States config
        sta_panel = QWidget()
        vbox_more.addWidget(sta_panel)
        hbox_sta = QHBoxLayout(sta_panel)
        hbox_sta.setContentsMargins(0, 0, 0, 0)
        hbox_sta.setSpacing(6)
        lbl_sta_col = QWidget()
        lbl_sta_col.setFixedWidth(LABEL_WIDTH)
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
        self.edit_sta = edit_sta = QLineEdit()
        edit_sta.setPlaceholderText("Filter observables...")
        edit_sta.setFixedWidth(192)
        self.check_only_sta = check_only_sta = QCheckBox("Show Checked Only")
        check_only_sta.setChecked(False)
        hbox_action_sta.addWidget(edit_sta)
        hbox_action_sta.addStretch()
        hbox_action_sta.addWidget(check_only_sta)

        self.sta_table = ObservableTable()
        self.sta_table.setMinimumHeight(120)
        vbox_sta_edit.addWidget(self.sta_table)
        hbox_sta.addWidget(edit_sta_col)

        cbox_more.setContentLayout(vbox_more)

    def config_logic(self):
        self.edit_var.textChanged.connect(self.filter_var)
        self.check_only_var.stateChanged.connect(self.toggle_var_show_mode)
        self.edit_obj.textChanged.connect(self.filter_obj)
        self.check_only_obj.stateChanged.connect(self.toggle_obj_show_mode)
        self.edit_con.textChanged.connect(self.filter_con)
        self.check_only_con.stateChanged.connect(self.toggle_con_show_mode)
        self.btn_env_params.toggled.connect(self.toggle_env_params)
        self.btn_algo_parans.toggled.connect(self.toggle_algorithm_params)
        self.refresh_current_btn.clicked.connect(self.var_table.refresh_current_values)

        self.obj_table.data_changed.connect(lambda: self.update_vocs("obj_table"))
        self.con_table.data_changed.connect(lambda: self.update_vocs("con_table"))
        self.sta_table.data_changed.connect(lambda: self.update_vocs("sta_table"))
        self.var_table.data_changed.connect(lambda: self.update_vocs("var_table"))

        self.env_cb.currentTextChanged.connect(self._on_env_selection_changed)

    def _on_env_selection_changed(self, env_name: str):
        self.env_name = env_name if env_name else None

    def update_vocs(self, origin: str):
        logger.debug(f"Emitting vocs_updated signal from env_cbox: {origin}")
        vocs, _ = self.compose_vocs()
        self.vocs_updated.emit(vocs)
        self.edit_algo_params.update_vocs(vocs)

    def toggle_env_params(self, checked: bool):
        if not checked:
            self.edit_env_params.hide()
        else:
            self.edit_env_params.setMinimumHeight(
                self._qtree_height_hint(self.edit_env_params)
            )
            self.edit_env_params.show()

    def toggle_algorithm_params(self, checked: bool):
        if not checked:
            self.edit_algo_params.hide()
        else:
            self.edit_algo_params.setMinimumHeight(
                self._qtree_height_hint(self.edit_algo_params)
            )
            self.edit_algo_params.show()

    def _qtree_height_hint(self, widget: QTreeWidget) -> int:
        # set height based on number of rows * row size
        # but somewhere between 50 and 200
        return min(widget.topLevelItemCount() * widget.sizeHintForRow(0) + 50, 200)

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
        self.obj_table.update_show_selected_only(self.check_only_obj.isChecked())

    def filter_obj(self):
        self.obj_table.update_keyword(self.edit_obj.text())

    def toggle_con_show_mode(self, _):
        self.con_table.update_show_selected_only(self.check_only_con.isChecked())

    def filter_con(self):
        self.con_table.update_keyword(self.edit_con.text())

    def toggle_sta_show_mode(self, _):
        self.sta_table.update_show_selected_only(self.check_only_sta.isChecked())

    def filter_sta(self):
        self.sta_table.update_keyword(self.edit_sta.text())

    def update_template_cb(self, template_name):
        """
        Change the displayed template name without emitting signals to
        reload
        """
        template_cb = self.template_cb
        if ".yaml" in template_name:
            template_name = template_name.replace(".yaml", "")
        if template_cb is not None:
            index = template_cb.findText(template_name)
            template_cb.blockSignals(True)
            if index >= 0:
                template_cb.setCurrentIndex(index)
            else:
                template_cb.addItem(template_name)
                template_cb.setCurrentIndex(template_cb.count() - 1)
            template_cb.blockSignals(False)
            self.template_row.sync_selection_state()

    def compose_vocs(self) -> tuple[VOCS, list[str]]:
        # Compose the VOCS settings
        variables = self.var_table.export_variables()

        objectives: dict[str, Any] = {}
        for objective in self.obj_table.export_data():
            obj_name = next(iter(objective))
            (rule,) = objective[obj_name]
            objectives[obj_name] = rule

        constraints: dict[str, list[float]] = {}
        critical_constraints: list[str] = []
        for constraint in self.con_table.export_data():
            con_name = next(iter(constraint))
            relation, threshold, critical = constraint[con_name]
            constraints[con_name] = [CONS_RELATION_DICT[relation], threshold]
            if critical:
                critical_constraints.append(con_name)

        observables: list[str] = []
        for observable in self.sta_table.export_data():
            obs_name = next(iter(observable))
            observables.append(obs_name)

        try:
            # We want to ensure it's a dict of either lists or ContinuousVariables
            variables = {
                k: list(v) if not isinstance(v, ContinuousVariable) else v
                for k, v in variables.items()
            }
            vocs = VOCS(
                variables=variables,
                objectives=objectives,
                constraints=constraints,
                constants={},
                observables=observables,
            )
        except ValidationError as e:
            raise BadgerRoutineError(
                f"\n\nVOCS validation failed: {format_validation_error(e)}"
            ) from e
        return vocs, critical_constraints
