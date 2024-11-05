from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QPlainTextEdit,
)
from PyQt5.QtWidgets import QComboBox, QCheckBox, QStyledItemDelegate, QLabel
from badger.gui.default.components.collapsible_box import CollapsibleBox
from badger.settings import init_settings
from badger.gui.default.utils import (
    MouseWheelWidgetAdjustmentGuard,
    NoHoverFocusComboBox,
)
from badger.utils import strtobool


class BadgerAlgoBox(CollapsibleBox):
    def __init__(self, parent=None, generators=[], scaling_functions=[]):
        super().__init__(parent, " Algorithm")

        self.generators = generators
        self.scaling_functions = scaling_functions

        self.init_ui()

    def init_ui(self):
        config_singleton = init_settings()

        vbox = QVBoxLayout()

        # Algo selector
        name = QWidget()
        hbox_name = QHBoxLayout(name)
        hbox_name.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Name")
        lbl.setFixedWidth(64)
        self.cb = cb = NoHoverFocusComboBox()
        cb.setItemDelegate(QStyledItemDelegate())
        cb.addItems(self.generators)
        cb.setCurrentIndex(-1)
        cb.installEventFilter(MouseWheelWidgetAdjustmentGuard(cb))
        hbox_name.addWidget(lbl)
        hbox_name.addWidget(cb, 1)
        self.btn_docs = btn_docs = QPushButton("Open Docs")
        btn_docs.setFixedSize(128, 24)
        hbox_name.addWidget(btn_docs)
        vbox.addWidget(name)

        # Algo params
        params = QWidget()
        hbox_params = QHBoxLayout(params)
        hbox_params.setContentsMargins(0, 0, 0, 0)
        lbl_params_col = QWidget()
        vbox_lbl_params = QVBoxLayout(lbl_params_col)
        vbox_lbl_params.setContentsMargins(0, 0, 0, 0)
        lbl_params = QLabel("Params")
        lbl_params.setFixedWidth(64)
        vbox_lbl_params.addWidget(lbl_params)
        vbox_lbl_params.addStretch(1)
        hbox_params.addWidget(lbl_params_col)

        edit_params_col = QWidget()
        vbox_params_edit = QVBoxLayout(edit_params_col)
        vbox_params_edit.setContentsMargins(0, 0, 0, 8)
        script_bar = QWidget()
        hbox_script = QHBoxLayout(script_bar)
        hbox_script.setContentsMargins(0, 0, 0, 0)
        vbox_params_edit.addWidget(script_bar)
        self.check_use_script = check_use_script = QCheckBox("Generate from Script")
        check_use_script.setChecked(False)
        self.btn_edit_script = btn_edit_script = QPushButton("Edit Script")
        btn_edit_script.setFixedSize(128, 24)
        btn_edit_script.hide()
        hbox_script.addWidget(check_use_script)
        hbox_script.addWidget(btn_edit_script)
        if not strtobool(config_singleton.read_value("BADGER_ENABLE_ADVANCED")):
            script_bar.hide()
        self.edit = edit = QPlainTextEdit()
        # edit.setMaximumHeight(80)
        edit.setMinimumHeight(480)
        vbox_params_edit.addWidget(edit)
        hbox_params.addWidget(edit_params_col)
        vbox.addWidget(params)

        cbox_misc = CollapsibleBox(self, " Domain Scaling")
        vbox.addWidget(cbox_misc)
        vbox_misc = QVBoxLayout()

        # Domain scaling
        scaling = QWidget()
        hbox_scaling = QHBoxLayout(scaling)
        hbox_scaling.setContentsMargins(0, 0, 0, 0)
        lbl_scaling_col = QWidget()
        vbox_lbl_scaling = QVBoxLayout(lbl_scaling_col)
        vbox_lbl_scaling.setContentsMargins(0, 0, 0, 0)
        lbl_scaling = QLabel("Type")
        lbl_scaling.setFixedWidth(64)
        vbox_lbl_scaling.addWidget(lbl_scaling)
        vbox_lbl_scaling.addStretch(1)
        hbox_scaling.addWidget(lbl_scaling_col)
        self.cb_scaling = cb_scaling = QComboBox()
        cb_scaling.setItemDelegate(QStyledItemDelegate())
        cb_scaling.addItems(self.scaling_functions)
        cb_scaling.setCurrentIndex(-1)
        hbox_scaling.addWidget(cb_scaling, 1)
        vbox_misc.addWidget(scaling)

        params_s = QWidget()
        hbox_params_s = QHBoxLayout(params_s)
        hbox_params_s.setContentsMargins(0, 0, 0, 0)
        lbl_params_s_col = QWidget()
        vbox_lbl_params_s = QVBoxLayout(lbl_params_s_col)
        vbox_lbl_params_s.setContentsMargins(0, 0, 0, 0)
        lbl_params_s = QLabel("Params")
        lbl_params_s.setFixedWidth(64)
        vbox_lbl_params_s.addWidget(lbl_params_s)
        vbox_lbl_params_s.addStretch(1)
        hbox_params_s.addWidget(lbl_params_s_col)
        self.edit_scaling = edit_scaling = QPlainTextEdit()
        edit_scaling.setMaximumHeight(80)
        hbox_params_s.addWidget(edit_scaling)
        vbox_misc.addWidget(params_s)

        cbox_misc.setContentLayout(vbox_misc)
        if not strtobool(config_singleton.read_value("BADGER_ENABLE_ADVANCED")):
            cbox_misc.hide()

        self.setContentLayout(vbox)
        # vbox.addStretch()
