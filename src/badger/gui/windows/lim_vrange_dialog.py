from copy import deepcopy

from PyQt5.QtWidgets import (
    QDialog,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QDoubleSpinBox,
    QRadioButton,
)
from PyQt5.QtWidgets import (
    QGroupBox,
    QLabel,
    QComboBox,
    QStyledItemDelegate,
    QStackedWidget,
)
from PyQt5.QtCore import Qt


class BadgerLimitVariableRangeDialog(QDialog):
    def __init__(
        self, parent, set_vrange, save_config, configs=None, apply_to_all=False
    ):
        super().__init__(parent)

        self.set_vrange = set_vrange
        self.save_config = save_config
        self.configs = deepcopy(configs)
        if configs is None:
            self.configs = {
                "limit_option_idx": 0,
                "ratio_curr": 0.1,
                "ratio_full": 0.1,
                "delta": 0.1,
            }
        self.apply_to_all = apply_to_all

        self.init_ui()
        self.config_logic()

    def init_ui(self):
        self.setWindowTitle("Set variable range")
        self.setMinimumWidth(360)

        vbox = QVBoxLayout(self)

        # Action bar
        action_bar = QWidget()
        hbox = QHBoxLayout(action_bar)
        hbox.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel("Set range by")
        # lbl.setFixedWidth(128)
        self.cb = cb = QComboBox()
        tooltip = """Ratio wrt current value will set the limit
with [ratio * current value] span,
while centering around the current value;

Ratio wrt full range will set the limit
with [ratio * variable range] span,
while centering around the current value;

No matter which option you choose, the limit
will be clipped by the variable range."""
        cb.setToolTip(tooltip)
        cb.setItemDelegate(QStyledItemDelegate())
        cb.addItems(
            [
                "ratio wrt current value",
                "ratio wrt full range",
                "delta around current value",
            ]
        )
        cb.setCurrentIndex(self.configs["limit_option_idx"])

        hbox.addWidget(lbl)
        hbox.addWidget(cb, 1)

        # Config group
        group_config = QGroupBox("Parameters")
        vbox_config = QVBoxLayout(group_config)

        self.stacks = stacks = QStackedWidget()
        # Ratio curr config
        ratio_curr_config = QWidget()
        hbox_ratio_curr = QHBoxLayout(ratio_curr_config)
        hbox_ratio_curr.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Ratio")
        self.sb_ratio_curr = sb_ratio_curr = QDoubleSpinBox()
        sb_ratio_curr.setMinimum(0)
        sb_ratio_curr.setMaximum(1)
        sb_ratio_curr.setValue(self.configs["ratio_curr"])
        sb_ratio_curr.setDecimals(2)
        sb_ratio_curr.setSingleStep(0.01)
        hbox_ratio_curr.addWidget(lbl)
        hbox_ratio_curr.addWidget(sb_ratio_curr, 1)
        # Ratio full config
        ratio_full_config = QWidget()
        hbox_ratio_full = QHBoxLayout(ratio_full_config)
        hbox_ratio_full.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Ratio")
        self.sb_ratio_full = sb_ratio_full = QDoubleSpinBox()
        sb_ratio_full.setMinimum(0)
        sb_ratio_full.setMaximum(1)
        sb_ratio_full.setValue(self.configs["ratio_full"])
        sb_ratio_full.setDecimals(2)
        sb_ratio_full.setSingleStep(0.01)
        hbox_ratio_full.addWidget(lbl)
        hbox_ratio_full.addWidget(sb_ratio_full, 1)
        # Delta config
        delta_config = QWidget()
        hbox_delta = QHBoxLayout(delta_config)
        hbox_delta.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Delta")
        self.sb_delta = sb_delta = QDoubleSpinBox()
        sb_delta.setMinimum(0)
        sb_delta.setMaximum(1e4)
        sb_delta.setValue(self.configs["delta"])
        sb_delta.setDecimals(6)
        sb_delta.setSingleStep(0.01)
        hbox_delta.addWidget(lbl)
        hbox_delta.addWidget(sb_delta, 1)

        stacks.addWidget(ratio_curr_config)
        stacks.addWidget(ratio_full_config)
        stacks.addWidget(delta_config)

        stacks.setCurrentIndex(self.configs["limit_option_idx"])
        vbox_config.addWidget(stacks)
        vbox_config.addStretch(1)

        # Apply to group
        apply_to_group = QWidget()
        hbox_apply_to = QHBoxLayout(apply_to_group)
        hbox_apply_to.setContentsMargins(0, 0, 0, 0)
        lbl_apply_to = QLabel("Apply to:")
        self.rb_all_variables = rb_all_variables = QRadioButton("All Variables")
        self.rb_only_visible = rb_only_visible = QRadioButton("Only Visible")

        if self.apply_to_all:
            rb_all_variables.setChecked(True)
        else:
            rb_only_visible.setChecked(True)  # Default selection
        hbox_apply_to.addWidget(lbl_apply_to)
        hbox_apply_to.addWidget(rb_all_variables)
        hbox_apply_to.addWidget(rb_only_visible)
        vbox_config.addWidget(apply_to_group)

        # Button set
        button_set = QWidget()
        hbox_set = QHBoxLayout(button_set)
        hbox_set.setContentsMargins(0, 0, 0, 0)
        self.btn_cancel = btn_cancel = QPushButton("Cancel")
        self.btn_set = btn_set = QPushButton("Set")
        btn_cancel.setFixedSize(96, 24)
        btn_set.setFixedSize(96, 24)
        hbox_set.addStretch()
        hbox_set.addWidget(btn_cancel)
        hbox_set.addWidget(btn_set)

        vbox.addWidget(action_bar)
        vbox.addWidget(group_config, 1)
        vbox.addWidget(button_set)

    def config_logic(self):
        self.cb.currentIndexChanged.connect(self.limit_option_changed)
        self.btn_cancel.clicked.connect(self.close)
        self.btn_set.clicked.connect(
            lambda: self.set(set_all=self.rb_all_variables.isChecked())
        )
        self.sb_ratio_curr.valueChanged.connect(self.ratio_curr_changed)
        self.sb_ratio_full.valueChanged.connect(self.ratio_full_changed)
        self.sb_delta.valueChanged.connect(self.delta_changed)

    def ratio_curr_changed(self, ratio_curr):
        self.configs["ratio_curr"] = ratio_curr

    def ratio_full_changed(self, ratio_full):
        self.configs["ratio_full"] = ratio_full

    def delta_changed(self, delta):
        self.configs["delta"] = delta

    def set(self, set_all: bool = True):
        self.save_config(self.configs)
        self.set_vrange(set_all=set_all)  # pass set_all flag to set_vrange
        self.close()

    def limit_option_changed(self, i):
        self.stacks.setCurrentIndex(i)

        # Update configs
        self.configs["limit_option_idx"] = i

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.set(set_all=self.rb_all_variables.isChecked())
        elif event.key() == Qt.Key_Escape:
            self.close()
