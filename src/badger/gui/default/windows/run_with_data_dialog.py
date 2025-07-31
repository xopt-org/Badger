from PyQt5.QtWidgets import (
    QDialog,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QCheckBox,
)
from PyQt5.QtWidgets import (
    QGroupBox,
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


class BadgerRunWithDataDialog(QDialog):
    def __init__(self, parent, run_opt, save_config):
        super().__init__(parent)

        self.run_opt = run_opt
        self.save_config = save_config
        self.configs = {}

        self.init_ui()
        self.config_logic()

    def init_ui(self):
        self.setWindowTitle("Run with data")
        self.setMinimumWidth(400)

        vbox = QVBoxLayout(self)

        # Action bar
        action_bar = QWidget()

        action_vbox = QVBoxLayout(action_bar)
        action_vbox.setContentsMargins(0, 0, 0, 0)

        # Config group
        group_config = QGroupBox("Data and Run Options")

        vbox_config = QVBoxLayout(group_config)

        # Widget for data options
        data_opts_config = QWidget()

        data_vbox = QVBoxLayout(data_opts_config)
        data_vbox.setContentsMargins(0, 0, 0, 0)

        self.run_data_checkbox = QCheckBox("Load data from displayed run")
        self.run_data_checkbox.setToolTip(
            "This will add the data from the currently displayed run \n to the new optimization"
        )
        self.init_points_checkbox = QCheckBox(
            "Resample initial points"
        )
        self.init_points_checkbox.setToolTip(
            "Sample points from the Initial Points Table before \n continuing optimization. Leave this unchecked to avoid sampling \n initial points, for example to continue the previous routine directly"
        )

        # Layout for data options widget
        data_vbox.addWidget(self.run_data_checkbox)
        data_vbox.addWidget(self.init_points_checkbox)

        generator_group = QGroupBox("Generator Options")
        vbox_generator = QVBoxLayout(generator_group)
        self.load_generator_data_checkbox = load_generator_data_checkbox = QCheckBox(
            "Load Xopt Generator Data from displayed run"
        )
        load_generator_data_checkbox.setToolTip(
            "Load data from displayed run generator into new Xopt Generator"
        )
        vbox_generator.addWidget(load_generator_data_checkbox)

        # Group
        vbox_config.addWidget(data_opts_config)
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
        vbox.addWidget(generator_group)
        vbox.addWidget(button_set)

        # Default options
        self.run_data_checkbox.setChecked(True)
        self.init_points_checkbox.setChecked(False)
        self.load_generator_data_checkbox.setChecked(True)

    def config_logic(self):
        self.btn_cancel.clicked.connect(self.close)
        self.btn_run.clicked.connect(self.run)

    def save_options(self):
        self.configs["run_data"] = self.run_data_checkbox.isChecked()
        self.configs["init_points"] = self.init_points_checkbox.isChecked()
        self.configs["generator_data"] = self.load_generator_data_checkbox.isChecked()

    def run(self):
        self.save_options()
        self.save_config(self.configs)
        print("dialog run")
        self.run_opt(
            use_termination_condition=False,
            use_data=True,
        )
        self.close()

    def closeEvent(self, event):
        self.save_options()
        self.save_config(self.configs)

        event.accept()
