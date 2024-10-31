from PyQt5.QtWidgets import QDialog, QWidget, QHBoxLayout, QStackedWidget
from PyQt5.QtWidgets import QVBoxLayout, QSpinBox, QPushButton
from PyQt5.QtWidgets import QGroupBox, QLabel, QComboBox, QStyledItemDelegate
from badger.gui.default.components.robust_spinbox import RobustSpinBox


class BadgerAddRandomDialog(QDialog):
    def __init__(self, parent, add_points, save_config, configs=None):
        super().__init__(parent)

        self.add_points = add_points
        self.save_config = save_config
        self.configs = configs
        if configs is None:
            self.configs = {
                "method": 0,
                "n_points": 3,
                "fraction": 0.1,
            }

        self.init_ui()
        self.config_logic()

    def init_ui(self):
        self.setWindowTitle("Add random points")
        self.setMinimumWidth(360)

        vbox = QVBoxLayout(self)

        # Action bar
        action_bar = QWidget()
        hbox = QHBoxLayout(action_bar)
        hbox.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel("Add points in")
        # lbl.setFixedWidth(64)
        self.cb = cb = QComboBox()
        cb.setItemDelegate(QStyledItemDelegate())
        cb.addItems(
            [
                "region around current value",
                # 'lhs',
            ]
        )
        cb.setCurrentIndex(self.configs["method"])

        hbox.addWidget(lbl)
        hbox.addWidget(cb, 1)

        # Config group
        group_config = QGroupBox("Parameters")
        vbox_config = QVBoxLayout(group_config)

        self.stacks = stacks = QStackedWidget()
        # Xopt config
        xopt_config = QWidget()
        vbox_xopt = QVBoxLayout(xopt_config)
        vbox_xopt.setContentsMargins(0, 0, 0, 0)
        hbox_xopt = QHBoxLayout()
        hbox_xopt.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Number of points")
        lbl.setFixedWidth(128)
        self.sb_np = sb_np = QSpinBox()
        sb_np.setMinimum(1)
        sb_np.setMaximum(100000)
        sb_np.setValue(self.configs["n_points"])
        sb_np.setSingleStep(1)
        hbox_xopt.addWidget(lbl)
        hbox_xopt.addWidget(sb_np, 1)
        vbox_xopt.addLayout(hbox_xopt)

        hbox_frac = QHBoxLayout()
        hbox_frac.setContentsMargins(0, 0, 0, 0)
        lbl_frac = QLabel("Fraction")
        lbl_frac.setFixedWidth(128)
        hbox_frac.addWidget(lbl_frac)
        self.sb_frac = sb_frac = RobustSpinBox(
            default_value=0.1, lower_bound=0.0, upper_bound=1.0, decimals=2
        )
        sb_frac.setValue(self.configs["fraction"])
        hbox_frac.addWidget(sb_frac, 1)
        vbox_xopt.addLayout(hbox_frac)

        stacks.addWidget(xopt_config)

        stacks.setCurrentIndex(self.configs["method"])
        vbox_config.addWidget(stacks)
        vbox_config.addStretch(1)

        # Button set
        button_set = QWidget()
        hbox_set = QHBoxLayout(button_set)
        hbox_set.setContentsMargins(0, 0, 0, 0)
        self.btn_cancel = btn_cancel = QPushButton("Cancel")
        self.btn_add = btn_add = QPushButton("Add")
        btn_cancel.setFixedSize(96, 24)
        btn_add.setFixedSize(96, 24)
        hbox_set.addStretch()
        hbox_set.addWidget(btn_cancel)
        hbox_set.addWidget(btn_add)

        vbox.addWidget(action_bar)
        vbox.addWidget(group_config, 1)
        vbox.addWidget(button_set)

    def config_logic(self):
        self.cb.currentIndexChanged.connect(self.method_changed)
        self.btn_cancel.clicked.connect(self.close)
        self.btn_add.clicked.connect(self.add)
        self.sb_np.valueChanged.connect(self.n_points_changed)
        self.sb_frac.valueChanged.connect(self.frac_changed)

    def n_points_changed(self, n_points):
        self.configs["n_points"] = n_points

    def frac_changed(self, frac):
        self.configs["fraction"] = frac

    def add(self):
        self.save_config(self.configs)
        self.add_points()
        self.close()

    def method_changed(self, i):
        self.stacks.setCurrentIndex(i)

        # Update configs
        self.configs["method"] = i

    def closeEvent(self, event):
        self.save_config(self.configs)

        event.accept()
