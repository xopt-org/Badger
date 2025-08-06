from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QPlainTextEdit,
)
from PyQt5.QtWidgets import QComboBox, QCheckBox, QStyledItemDelegate, QLabel
from PyQt5.QtCore import Qt
from badger.gui.default.components.collapsible_box import CollapsibleBox
from badger.settings import init_settings
from badger.gui.default.utils import (
    MouseWheelWidgetAdjustmentGuard,
    NoHoverFocusComboBox,
)
from badger.gui.default.components.data_table import (
    data_table,
)
from badger.gui.default.windows.load_data_from_run_dialog import (
    BadgerLoadDataFromRunDialog,
)
from badger.utils import strtobool

LABEL_WIDTH = 96


class BadgerAlgoBox(QWidget):
    def __init__(self, parent=None, generators=[], scaling_functions=[]):
        super().__init__(parent)

        self.generators = generators
        self.scaling_functions = scaling_functions

        self.init_ui()

    def init_ui(self):
        config_singleton = init_settings()

        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(8, 8, 8, 8)

        # Algo selector
        name = QWidget()
        hbox_name = QHBoxLayout(name)
        hbox_name.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Algorithm")
        lbl.setFixedWidth(LABEL_WIDTH)
        self.cb = cb = NoHoverFocusComboBox()
        cb.setItemDelegate(QStyledItemDelegate())
        cb.addItems(self.generators)
        cb.setCurrentIndex(-1)
        cb.installEventFilter(MouseWheelWidgetAdjustmentGuard(cb))
        hbox_name.addWidget(lbl)
        hbox_name.addWidget(cb, 1)
        self.btn_docs = btn_docs = QPushButton("Open Docs")
        btn_docs.setFixedSize(96, 24)
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
        lbl_params.setFixedWidth(LABEL_WIDTH)
        vbox_lbl_params.addWidget(lbl_params)
        vbox_lbl_params.addStretch(1)
        hbox_params.addWidget(lbl_params_col)

        edit_params_col = QWidget()
        vbox_params_edit = QVBoxLayout(edit_params_col)
        vbox_params_edit.setContentsMargins(0, 0, 0, 0)
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
        edit.setMinimumHeight(200)
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
        lbl_params_s.setFixedWidth(LABEL_WIDTH)
        vbox_lbl_params_s.addWidget(lbl_params_s)
        vbox_lbl_params_s.addStretch(1)
        hbox_params_s.addWidget(lbl_params_s_col)
        self.edit_scaling = edit_scaling = QPlainTextEdit()
        edit_scaling.setMaximumHeight(80)
        hbox_params_s.addWidget(edit_scaling)
        vbox_misc.addWidget(params_s)

        # Add table for loading data into generator
        # widget for layout
        load_data = QWidget()
        vbox_load_data = QVBoxLayout(load_data)
        vbox_load_data.setContentsMargins(0, 0, 0, 0)
        vbox_load_data.setAlignment(Qt.AlignLeft)

        # Add label, buttons for loading data and clear table
        load_data_options = QWidget()
        hbox_load_data_options = QHBoxLayout(load_data_options)
        hbox_load_data_options.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Data (Optional)")
        lbl.setFixedWidth(LABEL_WIDTH + 2)
        hbox_load_data_options.addWidget(lbl)
        
        self.btn_load_data = QPushButton("Load Data")
        self.btn_load_data.clicked.connect(self.load_data)
        self.btn_load_data.setFixedSize(96, 24)
        self.btn_reset_table = QPushButton("Clear Table")
        self.btn_reset_table.clicked.connect(self.reset_table)
        self.btn_reset_table.setFixedSize(96, 24)
        hbox_load_data_options.addWidget(self.btn_load_data)
        hbox_load_data_options.addWidget(self.btn_reset_table)
        hbox_load_data_options.setAlignment(Qt.AlignLeft)
        vbox_load_data.addWidget(load_data_options)

        # Data Table
        data_table_widget = QWidget()
        hbox_data_table = QHBoxLayout(data_table_widget)
        hbox_data_table.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("")
        lbl.setFixedWidth(LABEL_WIDTH - 5)
        hbox_data_table.addWidget(lbl)
        self.data_table = data_table()
        self.data_table.set_uneditable()
        self.data_table.setMinimumHeight(200)
        hbox_data_table.addWidget(self.data_table)
        vbox_load_data.addWidget(data_table_widget)

        vbox.addWidget(load_data)

        cbox_misc.setContentLayout(vbox_misc)
        if not strtobool(config_singleton.read_value("BADGER_ENABLE_ADVANCED")):
            cbox_misc.hide()

        # vbox.addStretch()

    def load_data(self):
        """
        Opens a dialog window for loading data into generator.
        """
        dlg = BadgerLoadDataFromRunDialog(
            parent=self,
            data_table=self.data_table,
        )
        self.tc_dialog = dlg
        try:
            dlg.exec()
        finally:
            self.tc_dialog = None
    
    def reset_table(self):
        self.data_table.clear()
        self.data_table.setRowCount(0)
        self.data_table.setColumnCount(0)
