from PyQt5.QtWidgets import (
    QDialog,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QSpinBox,
    QDoubleSpinBox,
)
from PyQt5.QtWidgets import (
    QGroupBox,
    QLabel,
    QComboBox,
    QStyledItemDelegate,
    QStackedWidget,
)


stylesheet_run = """
QPushButton:hover:pressed
{
    background-color: #92D38C;
}
QPushButton:hover
{
    background-color: #6EC566;
}
QPushButton
{
    background-color: #4AB640;
    color: #000000;
}
"""


class BadgerTerminationConditionDialog(QDialog):
    def __init__(self, parent, run_opt, save_config, configs=None):
        super().__init__(parent)

        self.run_opt = run_opt
        self.save_config = save_config
        self.configs = configs
        if configs is None:
            self.configs = {"tc_idx": 0, "max_eval": 42, "max_time": 600, "ftol": 0}

        self.init_ui()
        self.config_logic()

    def init_ui(self):
        self.setWindowTitle("Optimization termination condition")
        self.setMinimumWidth(360)

        vbox = QVBoxLayout(self)

        # Action bar
        action_bar = QWidget()
        hbox = QHBoxLayout(action_bar)
        hbox.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel("Run until")
        lbl.setFixedWidth(64)
        self.cb = cb = QComboBox()
        cb.setItemDelegate(QStyledItemDelegate())
        cb.addItems(
            [
                "maximum evaluation reached",
                "maximum running time exceeded",
                # 'optimization converged',
            ]
        )
        cb.setCurrentIndex(self.configs["tc_idx"])

        hbox.addWidget(lbl)
        hbox.addWidget(cb, 1)

        # Config group
        group_config = QGroupBox("Termination Condition")
        vbox_config = QVBoxLayout(group_config)

        self.stacks = stacks = QStackedWidget()
        # Max evaluation config
        max_eval_config = QWidget()
        hbox_max_eval = QHBoxLayout(max_eval_config)
        hbox_max_eval.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Max evaluation")
        self.sb_max_eval = sb_max_eval = QSpinBox()
        sb_max_eval.setMinimum(1)
        sb_max_eval.setMaximum(100000)
        sb_max_eval.setValue(self.configs["max_eval"])
        sb_max_eval.setSingleStep(1)
        hbox_max_eval.addWidget(lbl)
        hbox_max_eval.addWidget(sb_max_eval, 1)
        # Max running time config
        max_time_config = QWidget()
        hbox_max_time = QHBoxLayout(max_time_config)
        hbox_max_time.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Timeout (sec)")
        self.sb_max_time = sb_max_time = QDoubleSpinBox()
        sb_max_time.setMinimum(0.0)
        sb_max_time.setMaximum(86400)
        sb_max_time.setValue(self.configs["max_time"])
        sb_max_time.setDecimals(2)
        sb_max_time.setSingleStep(0.1)
        hbox_max_time.addWidget(lbl)
        hbox_max_time.addWidget(sb_max_time, 1)
        # Tolerance config
        tol_config = QWidget()
        hbox_tol = QHBoxLayout(tol_config)
        hbox_tol.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Tolerance on objective")
        self.sb_tol = sb_tol = QDoubleSpinBox()
        sb_tol.setMinimum(0.0)
        sb_tol.setMaximum(1000)
        sb_tol.setValue(self.configs["ftol"])
        sb_tol.setDecimals(4)
        sb_tol.setSingleStep(0.001)
        hbox_tol.addWidget(lbl)
        hbox_tol.addWidget(sb_tol, 1)

        stacks.addWidget(max_eval_config)
        stacks.addWidget(max_time_config)
        stacks.addWidget(tol_config)

        stacks.setCurrentIndex(self.configs["tc_idx"])
        vbox_config.addWidget(stacks)
        vbox_config.addStretch(1)

        # Button set
        button_set = QWidget()
        hbox_set = QHBoxLayout(button_set)
        hbox_set.setContentsMargins(0, 0, 0, 0)
        self.btn_cancel = btn_cancel = QPushButton("Cancel")
        self.btn_run = btn_run = QPushButton("Run")
        btn_run.setStyleSheet(stylesheet_run)
        btn_cancel.setFixedSize(96, 24)
        btn_run.setFixedSize(96, 24)
        hbox_set.addStretch()
        hbox_set.addWidget(btn_cancel)
        hbox_set.addWidget(btn_run)

        vbox.addWidget(action_bar)
        vbox.addWidget(group_config, 1)
        vbox.addWidget(button_set)

    def config_logic(self):
        self.cb.currentIndexChanged.connect(self.terminition_condition_changed)
        self.btn_cancel.clicked.connect(self.close)
        self.btn_run.clicked.connect(self.run)
        self.sb_max_eval.valueChanged.connect(self.max_eval_changed)
        self.sb_max_time.valueChanged.connect(self.max_time_changed)
        self.sb_tol.valueChanged.connect(self.ftol_changed)

    def max_eval_changed(self, max_eval):
        self.configs["max_eval"] = max_eval

    def max_time_changed(self, max_time):
        self.configs["max_time"] = max_time

    def ftol_changed(self, ftol):
        self.configs["ftol"] = ftol

    def run(self):
        self.save_config(self.configs)
        self.run_opt(True)
        self.close()

    def terminition_condition_changed(self, i):
        self.stacks.setCurrentIndex(i)

        # Update configs
        self.configs["tc_idx"] = i

    def closeEvent(self, event):
        self.save_config(self.configs)

        event.accept()
