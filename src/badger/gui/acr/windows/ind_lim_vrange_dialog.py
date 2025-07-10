from copy import deepcopy

from PyQt5.QtWidgets import (
    QDialog,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QDoubleSpinBox,
    QGroupBox,
    QLabel,
    QComboBox,
    QStyledItemDelegate,
    QStackedWidget,
    QLineEdit,
    QFrame,
)
from PyQt5.QtCore import Qt


class BadgerIndividualLimitVariableRangeDialog(QDialog):
    def __init__(self, parent, name, apply_config, configs=None):
        super().__init__(parent)

        self.name = name
        self.apply_config = apply_config
        self.configs = deepcopy(configs)
        if configs is None:
            self.configs = {}

        self.init_ui()
        self.config_logic()

    def init_ui(self):
        self.setWindowTitle(f"Config variable {self.name}")
        self.setMinimumWidth(360)

        vbox = QVBoxLayout(self)

        # Add the new rows above "Set range by"
        info_group = QWidget()
        vbox_info = QVBoxLayout(info_group)
        vbox_info.setContentsMargins(0, 0, 0, 0)

        # Current value row
        hbox_current = QHBoxLayout()
        lbl_current = QLabel("Current value")
        lbl_current.setFixedWidth(128)
        self.lbl_current_value = lbl_current_value = QLineEdit(
            f"{self.configs.get('current_value', 0):.2f}"
        )
        hbox_current.addWidget(lbl_current)
        hbox_current.addWidget(lbl_current_value, 1)

        # Hard lower bound row
        hbox_lower = QHBoxLayout()
        lbl_lower = QLabel("Hard lower bound")
        lbl_lower.setFixedWidth(128)
        self.lbl_hard_lower = lbl_hard_lower = QLineEdit(
            f"{self.configs.get('lower_bound', 0):.2f}"
        )
        hbox_lower.addWidget(lbl_lower)
        hbox_lower.addWidget(lbl_hard_lower, 1)

        # Hard upper bound row
        hbox_upper = QHBoxLayout()
        lbl_upper = QLabel("Hard upper bound")
        lbl_upper.setFixedWidth(128)
        self.lbl_hard_upper = lbl_hard_upper = QLineEdit(
            f"{self.configs.get('upper_bound', 0):.2f}"
        )
        hbox_upper.addWidget(lbl_upper)
        hbox_upper.addWidget(lbl_hard_upper, 1)

        # Add the rows to the info group
        vbox_info.addLayout(hbox_current)
        vbox_info.addLayout(hbox_lower)
        vbox_info.addLayout(hbox_upper)

        # Add the info group to the main layout
        vbox.addWidget(info_group)

        # Add a horizontal separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)  # Horizontal line
        separator.setFrameShadow(QFrame.Sunken)  # Sunken style
        vbox.addWidget(separator)

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
        cb.setCurrentIndex(self.configs.get("limit_option_idx", 0))

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
        sb_ratio_curr.setValue(self.configs.get("ratio_curr", 0.1))
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
        sb_ratio_full.setValue(self.configs.get("ratio_full", 0.1))
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
        sb_delta.setValue(self.configs.get("delta", 0.1))
        sb_delta.setDecimals(6)
        sb_delta.setSingleStep(0.01)
        hbox_delta.addWidget(lbl)
        hbox_delta.addWidget(sb_delta, 1)

        stacks.addWidget(ratio_curr_config)
        stacks.addWidget(ratio_full_config)
        stacks.addWidget(delta_config)

        stacks.setCurrentIndex(self.configs.get("limit_option_idx", 0))
        vbox_config.addWidget(stacks)
        vbox_config.addStretch(1)

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
        self.btn_set.clicked.connect(self.set)
        self.sb_ratio_curr.valueChanged.connect(self.ratio_curr_changed)
        self.sb_ratio_full.valueChanged.connect(self.ratio_full_changed)
        self.sb_delta.valueChanged.connect(self.delta_changed)

    def update_config(self):
        try:
            lower = float(self.lbl_hard_lower.text())
            upper = float(self.lbl_hard_upper.text())
            self.configs["lower_bound"] = lower
            self.configs["upper_bound"] = upper
            # Fill in default values if not exist
            if "limit_option_idx" not in self.configs:
                self.configs["limit_option_idx"] = self.cb.currentIndex()
            if "ratio_curr" not in self.configs:
                self.configs["ratio_curr"] = self.sb_ratio_curr.value()
            if "ratio_full" not in self.configs:
                self.configs["ratio_full"] = self.sb_ratio_full.value()
            if "delta" not in self.configs:
                self.configs["delta"] = self.sb_delta.value()
        except ValueError:
            pass  # Optionally handle invalid input

    def ratio_curr_changed(self, ratio_curr):
        self.configs["ratio_curr"] = ratio_curr

    def ratio_full_changed(self, ratio_full):
        self.configs["ratio_full"] = ratio_full

    def delta_changed(self, delta):
        self.configs["delta"] = delta

    def set(self):
        self.update_config()
        self.apply_config(self.name, self.configs)
        self.close()

    def limit_option_changed(self, i):
        self.stacks.setCurrentIndex(i)

        # Update configs
        self.configs["limit_option_idx"] = i

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.set()
        elif event.key() == Qt.Key_Escape:
            self.close()
