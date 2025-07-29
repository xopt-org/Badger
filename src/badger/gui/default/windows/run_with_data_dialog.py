from PyQt5.QtWidgets import (
    QDialog,
    QWidget,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QRadioButton,
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
        
        lbl = QLabel("Select desired behavior preset: ")
        self.preset_cb = QComboBox()
        self.preset_cb.addItems([
            "Continue previous run",
            "Use model from previous run for new optimization",
            "Continue selected run with parameter updates",
            "Use displayed parameters for new optimization",
        ])
        self.preset_cb.setCurrentIndex(-1)
        self.preset_cb.activated.connect(self._select_options)
            
        action_vbox.addWidget(lbl)
        action_vbox.addWidget(self.preset_cb, 1)

        

        # Config group
        group_config = QGroupBox("Data and Run Options")

        vbox_config = QVBoxLayout(group_config)

        # Widget for data options
        data_opts_config = QWidget()

        data_vbox = QVBoxLayout(data_opts_config)
        data_vbox.setContentsMargins(0, 0, 0, 0)

        self.run_data_checkbox = run_data_checkbox = QCheckBox("Load data from displayed run")
        run_data_checkbox.setToolTip("This will add the data from the currently displayed run \n to the new optimization") 
        run_data_checkbox.clicked.connect(lambda: self.preset_cb.setCurrentIndex(-1)) 
        self.init_points_checkbox = init_points_checkbox = QCheckBox("Resample initial points")
        init_points_checkbox.setToolTip("Sample points from the Initial Points Table before \n continuing optimization. Leave this unchecked to avoid sampling \n initial points, for example to continue the previous routine directly")
        init_points_checkbox.clicked.connect(lambda: self.preset_cb.setCurrentIndex(-1)) 
        # run_from_current = QCheckBox("Run from current variable values")
        # run_from_current.setToolTip("Leaving this unchecked will load the currently displayed variable ranges into the new routine")

        # Layout for data options widget




        data_vbox.addWidget(run_data_checkbox)
        data_vbox.addWidget(init_points_checkbox)
        # data_vbox.addWidget(run_from_current)



        generator_group = QGroupBox("Generator Options")

        vbox_generator = QVBoxLayout(generator_group)

        # self.no_generator = QRadioButton("None -- use parameters from GUI to create new generator")
        # self.generator_data = QRadioButton("Load Xopt Generator Data from displayed run")
        # self.generator_full = QRadioButton("Load Full Xopt Generator from displayed run")
        
        # self.no_generator.clicked.connect(lambda: self.preset_cb.setCurrentIndex(-1)) 

        self.load_generator_data_checkbox = load_generator_data_checkbox = QCheckBox("Load Xopt Generator Data from displayed run")
        load_generator_data_checkbox.setToolTip("Load data from displayed run generator into new Xopt Generator")
        load_generator_data_checkbox.clicked.connect(lambda: self.preset_cb.setCurrentIndex(-1)) 
        self.load_generator_checkbox = load_generator_checkbox = QCheckBox("Load Xopt Generator Params")
        load_generator_checkbox.clicked.connect(lambda: self.preset_cb.setCurrentIndex(-1)) 

        # vbox_generator.addWidget(self.no_generator)
        # vbox_generator.addWidget(self.generator_data)
        # vbox_generator.addWidget(self.generator_full)
        vbox_generator.addWidget(load_generator_data_checkbox)
        vbox_generator.addWidget(load_generator_checkbox)


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
        
        self.preset_cb.setCurrentIndex(0)
        self._select_options()
    
    def _select_options(self):
        index = self.preset_cb.currentIndex()
        if index == 0: # continue prev run
            self.run_data_checkbox.setChecked(True)
            self.init_points_checkbox.setChecked(False)
            self.load_generator_data_checkbox.setChecked(True)
            self.load_generator_checkbox.setChecked(True)
        elif index == 1: # use generator for new optimization
            self.run_data_checkbox.setChecked(False)
            self.init_points_checkbox.setChecked(True)
            self.load_generator_data_checkbox.setChecked(True)
            self.load_generator_checkbox.setChecked(True)
        elif index == 2: # Continue selected with new params
            self.run_data_checkbox.setChecked(True)
            self.init_points_checkbox.setChecked(False)
            self.load_generator_data_checkbox.setChecked(True)
            self.load_generator_checkbox.setChecked(False)
        elif index == 3: # Use settings for new run
            self.run_data_checkbox.setChecked(False)
            self.init_points_checkbox.setChecked(True)
            self.load_generator_data_checkbox.setChecked(False)
            self.load_generator_checkbox.setChecked(False)

    def config_logic(self):
        # self.cb.currentIndexChanged.connect(self.terminition_condition_changed)
        self.btn_cancel.clicked.connect(self.close)
        self.btn_run.clicked.connect(self.run)
        # self.sb_max_eval.valueChanged.connect(self.max_eval_changed)
        # self.sb_max_time.valueChanged.connect(self.max_time_changed)
        # self.sb_tol.valueChanged.connect(self.ftol_changed)

        
    def save_options(self):
        self.configs["run_data"] = self.run_data_checkbox.isChecked()
        self.configs["init_points"] = self.init_points_checkbox.isChecked()
        self.configs["generator_data"] = self.load_generator_data_checkbox.isChecked()
        self.configs["generator_params"] = self.load_generator_checkbox.isChecked()

    def run(self):
        self.save_options()
        self.save_config(self.configs)
        print("dialog run")
        self.run_opt(
            use_termination_condition = False,
            use_data = True,
            )
        self.close()

    def closeEvent(self, event):
        self.save_options()
        self.save_config(self.configs)

        event.accept()