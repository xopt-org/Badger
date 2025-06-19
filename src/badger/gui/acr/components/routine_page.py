import warnings
import traceback
import copy
from functools import partial
import os
import yaml

import numpy as np
import pandas as pd
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import QLineEdit, QLabel, QPushButton, QFileDialog
from PyQt5.QtWidgets import QListWidgetItem, QMessageBox, QWidget, QTabWidget
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QScrollArea
from PyQt5.QtWidgets import QTableWidgetItem, QPlainTextEdit
from coolname import generate_slug
from xopt import VOCS
from xopt.generators import (
    get_generator_defaults,
    all_generator_names,
    get_generator_dynamic,
)
from xopt.utils import get_local_region
from pydantic import ValidationError

from badger.gui.acr.components.generator_cbox import BadgerAlgoBox
from badger.gui.default.components.data_table import (
    get_table_content_as_dict,
    set_init_data_table,
    update_init_data_table,
)
from badger.gui.acr.components.env_cbox import BadgerEnvBox
from badger.gui.default.components.filter_cbox import BadgerFilterBox
from badger.gui.default.components.state_item import state_item
from badger.gui.default.windows.docs_window import BadgerDocsWindow
from badger.gui.default.windows.env_docs_window import BadgerEnvDocsWindow
from badger.gui.default.windows.edit_script_dialog import BadgerEditScriptDialog
from badger.gui.default.windows.lim_vrange_dialog import BadgerLimitVariableRangeDialog
from badger.gui.acr.windows.ind_lim_vrange_dialog import (
    BadgerIndividualLimitVariableRangeDialog,
)
from badger.gui.default.windows.review_dialog import BadgerReviewDialog
from badger.gui.default.windows.add_random_dialog import BadgerAddRandomDialog
from badger.gui.default.windows.message_dialog import BadgerScrollableMessageBox
from badger.gui.default.utils import filter_generator_config
from badger.gui.acr.components.archive_search import ArchiveSearchWidget
from badger.archive import update_run
from badger.environment import instantiate_env
from badger.errors import (
    BadgerRoutineError,
    BadgerEnvVarError,
    BadgerEnvInstantiationError,
    VariableRangeError,
)
from badger.factory import list_generators, list_env, get_env
from badger.routine import Routine
from badger.settings import init_settings
from datetime import datetime
from badger.utils import (
    get_yaml_string,
    load_config,
    strtobool,
    get_badger_version,
    get_xopt_version,
)

LABEL_WIDTH = 96


def format_validation_error(e: ValidationError) -> str:
    """Convert Pydantic ValidationError into a friendly message."""
    messages = ["\n"]
    for err in e.errors():
        loc = " -> ".join(str(item) for item in err["loc"])
        msg = f"{loc}: {err['msg']}\n"
        messages.append(msg)
    return "\n".join(messages)


class BadgerRoutinePage(QWidget):
    sig_updated = pyqtSignal(str, str)  # routine name, routine description
    sig_load_template = pyqtSignal(str)  # template path
    sig_save_template = pyqtSignal(str)  # template path

    def __init__(self):
        super().__init__()

        self.generators = list_generators()
        self.envs = list_env()
        self.env = None
        self.routine = None
        self.script = ""
        self.window_docs = BadgerDocsWindow(self, "")
        self.window_env_docs = BadgerEnvDocsWindow(self, "")
        self.vars_env = None  # needed for passing env vars to the var table

        # Limit variable ranges
        self.limit_option = {
            "limit_option_idx": 0,
            "ratio_curr": 0.1,
            "ratio_full": 0.1,
            "delta": 0.1,
        }

        # Add radom points config
        self.add_rand_config = {
            "method": 0,
            "n_points": 3,
            "fraction": 0.1,
        }
        self.rc_dialog = None

        # Record the initial table actions
        self.init_table_actions = []
        # Record the ratio var ranges
        self.ratio_var_ranges = {}
        # Record the overrided variable ranges
        self.var_hard_limit = {}

        self.init_ui()
        self.config_logic()

        # Trigger the re-rendering of the environment box
        self.env_box.relative_to_curr.setChecked(True)
        # remember user selection from lim_vrange_dialog gui
        # 2: not initialized, 1: apply to all, 0: apply to only visible
        self.lim_apply_to_vars = 2

    def init_ui(self):
        config_singleton = init_settings()

        # Set up the layout
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(8, 18, 8, 0)

        self.tabs = tabs = QTabWidget()
        vbox.addWidget(tabs)

        # Meta group
        self.group_meta = group_meta = QWidget()
        vbox_meta = QVBoxLayout(group_meta)
        vbox_meta.setContentsMargins(8, 8, 8, 8)
        tabs.addTab(group_meta, "Metadata")

        # Name
        name = QWidget()
        hbox_name = QHBoxLayout(name)
        hbox_name.setContentsMargins(0, 0, 0, 0)
        label = QLabel("Name")
        label.setFixedWidth(LABEL_WIDTH)
        self.edit_save = edit_save = QLineEdit()
        edit_save.setPlaceholderText(generate_slug(2))
        hbox_name.addWidget(label)
        hbox_name.addWidget(edit_save, 1)
        vbox_meta.addWidget(name, alignment=Qt.AlignTop)

        # Description
        descr = QWidget()
        hbox_descr = QHBoxLayout(descr)
        hbox_descr.setContentsMargins(0, 0, 0, 0)
        lbl_descr_col = QWidget()
        vbox_lbl_descr = QVBoxLayout(lbl_descr_col)
        vbox_lbl_descr.setContentsMargins(0, 0, 0, 0)
        lbl_descr = QLabel("Description")
        lbl_descr.setFixedWidth(LABEL_WIDTH)
        vbox_lbl_descr.addWidget(lbl_descr)
        vbox_lbl_descr.addStretch(1)
        hbox_descr.addWidget(lbl_descr_col)

        edit_descr_col = QWidget()
        vbox_descr_edit = QVBoxLayout(edit_descr_col)
        vbox_descr_edit.setContentsMargins(0, 0, 0, 0)
        self.edit_descr = edit_descr = QPlainTextEdit()
        edit_descr.setMinimumHeight(80)
        vbox_descr_edit.addWidget(edit_descr)
        descr_bar = QWidget()
        hbox_descr_bar = QHBoxLayout(descr_bar)
        hbox_descr_bar.setContentsMargins(0, 0, 0, 0)
        self.btn_descr_update = btn_update = QPushButton("Update Description")
        btn_update.setDisabled(True)
        btn_update.setFixedSize(128, 24)
        hbox_descr_bar.addStretch(1)
        hbox_descr_bar.addWidget(btn_update)
        vbox_descr_edit.addWidget(descr_bar)
        hbox_descr.addWidget(edit_descr_col)
        vbox_meta.addWidget(descr)
        descr_bar.hide()

        # Save Template Button
        template_button = QWidget()
        hbox_name = QHBoxLayout(template_button)
        hbox_name.setContentsMargins(0, 0, 0, 0)
        self.save_template_button = save_template_button = QPushButton(
            "Save as Template"
        )
        save_template_button.setFixedSize(128, 24)
        hbox_name.addWidget(save_template_button, alignment=Qt.AlignRight)
        vbox_meta.addWidget(template_button, alignment=Qt.AlignBottom)
        template_button.show()

        # Tags
        self.cbox_tags = cbox_tags = BadgerFilterBox(title=" Tags")
        if not strtobool(config_singleton.read_value("BADGER_ENABLE_ADVANCED")):
            cbox_tags.hide()
        vbox_meta.addWidget(cbox_tags, alignment=Qt.AlignTop)
        # vbox_meta.addStretch()

        # vbox.addWidget(group_meta)

        # Env box
        self.BADGER_PLUGIN_ROOT = BADGER_PLUGIN_ROOT = config_singleton.read_value(
            "BADGER_PLUGIN_ROOT"
        )
        env_dict_dir = os.path.join(
            BADGER_PLUGIN_ROOT, "environments", "env_colors.yaml"
        )
        try:
            with open(env_dict_dir, "r") as stream:
                env_dict = yaml.safe_load(stream)
        except (FileNotFoundError, yaml.YAMLError):
            env_dict = {}
        self.env_box = BadgerEnvBox(env_dict, None, self.envs)
        scroll_area = QScrollArea()
        scroll_area.setFrameShape(QScrollArea.NoFrame)
        scroll_area.setStyleSheet(
            """
            QScrollArea {
                border: none;  /* Remove border */
                margin: 0px;   /* Remove margin */
                padding: 0px;  /* Remove padding */
            }
            QScrollArea > QWidget {
                margin: 0px;   /* Remove margin inside */
            }
        """
        )
        scroll_content_env = QWidget()
        scroll_layout_env = QVBoxLayout(scroll_content_env)
        scroll_layout_env.setContentsMargins(0, 0, 15, 0)
        scroll_layout_env.addWidget(self.env_box)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_content_env)
        tabs.addTab(scroll_area, "Environment + VOCS")

        # Algo box
        self.generator_box = BadgerAlgoBox(None, self.generators)
        tabs.addTab(self.generator_box, "Algorithm")

        tabs.setCurrentIndex(1)  # Show the env box by default

        # vbox.addStretch()

        # Template path
        try:
            self.template_dir = config_singleton.read_value("BADGER_TEMPLATE_ROOT")
        except KeyError:
            self.template_dir = os.path.join(self.BADGER_PLUGIN_ROOT, "templates")

    def config_logic(self):
        self.btn_descr_update.clicked.connect(self.update_description)
        self.env_box.load_template_button.clicked.connect(self.load_template_yaml)
        self.save_template_button.clicked.connect(self.save_template_yaml)
        self.generator_box.cb.currentIndexChanged.connect(self.select_generator)
        self.generator_box.btn_docs.clicked.connect(self.open_generator_docs)
        self.generator_box.check_use_script.stateChanged.connect(self.toggle_use_script)
        self.generator_box.btn_edit_script.clicked.connect(self.edit_script)
        self.env_box.cb.currentIndexChanged.connect(self.select_env)
        self.env_box.btn_env_play.clicked.connect(self.open_playground)
        self.env_box.btn_pv.clicked.connect(self.open_archive_search)
        self.env_box.btn_docs.clicked.connect(self.open_environment_docs)
        self.env_box.btn_add_var.clicked.connect(self.add_var)
        self.env_box.btn_lim_vrange.clicked.connect(self.limit_variable_ranges)
        self.env_box.btn_add_con.clicked.connect(self.add_constraint)
        self.env_box.btn_add_sta.clicked.connect(self.add_state)
        self.env_box.btn_add_curr.clicked.connect(
            partial(self.fill_curr_in_init_table, record=True)
        )
        self.env_box.btn_add_rand.clicked.connect(self.show_add_rand_dialog)
        self.env_box.btn_clear.clicked.connect(
            partial(self.clear_init_table, reset_actions=True)
        )
        self.env_box.btn_add_row.clicked.connect(self.add_row_to_init_table)
        self.env_box.relative_to_curr.stateChanged.connect(self.toggle_relative_to_curr)
        self.env_box.btn_refresh.clicked.connect(self.refresh_variables)
        self.env_box.var_table.sig_sel_changed.connect(self.update_init_table)
        self.env_box.var_table.sig_pv_added.connect(self.handle_pv_added)
        self.env_box.var_table.sig_var_config.connect(self.handle_var_config)

    def load_template_yaml(self) -> None:
        """
        Load data from template .yaml into template_dict dictionary.
        This function expects to be called via an action from
        a QPushButton
        """

        if isinstance(self.sender(), QPushButton):
            # load template from button
            options = QFileDialog.Options()
            template_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select YAML File",
                self.template_dir,
                "YAML Files (*.yaml);;All Files (*)",
                options=options,
            )

        if not template_path:
            return

        # Load template file
        try:
            with open(template_path, "r") as stream:
                template_dict = yaml.safe_load(stream)
                self.set_options_from_template(template_dict=template_dict)
                self.sig_load_template.emit(
                    f"Options loaded from template: {os.path.basename(template_path)}"
                )
        except (FileNotFoundError, yaml.YAMLError) as e:
            print(f"Error loading template: {e}")
            return

    def set_options_from_template(self, template_dict: dict):
        """
        Fills in routine_page GUI with relevant info from template_dict
        dictionary
        """

        # Compose the template
        try:
            name = template_dict["name"]
            description = template_dict["description"]
            relative_to_current = template_dict["relative_to_current"]
            generator_name = template_dict["generator"]["name"]
            env_name = template_dict["environment"]["name"]
            vrange_limit_options = template_dict["vrange_limit_options"]
            try:  # this one is optional
                vrange_hard_limit = template_dict["vrange_hard_limit"]
            except KeyError:
                vrange_hard_limit = {}
            initial_point_actions = template_dict[
                "initial_point_actions"
            ]  # should be type: add_curr
            critical_constraint_names = template_dict["critical_constraint_names"]
            env_params = template_dict["environment"]["params"]
        except KeyError as e:
            QMessageBox.warning(self, "Error", f"Missing key in template: {e}")
            return

        # set vocs
        vocs = VOCS(
            variables=template_dict["vocs"]["variables"],
            objectives=template_dict["vocs"]["objectives"],
            constraints=template_dict["vocs"]["constraints"],
            constants={},
            observables=template_dict["vocs"]["observables"],
        )

        # set name
        self.edit_save.setText(name)

        # set description
        self.edit_descr.setPlainText(description)

        # set generator
        if generator_name in self.generators:
            i = self.generators.index(generator_name)
            self.generator_box.cb.setCurrentIndex(i)

            filtered_config = filter_generator_config(
                generator_name, template_dict["generator"]
            )
            self.generator_box.edit.setPlainText(get_yaml_string(filtered_config))

        # set environment
        if env_name in self.envs:
            i = self.envs.index(env_name)
            self.env_box.cb.setCurrentIndex(i)
            self.env_box.edit.setPlainText(get_yaml_string(env_params))

        # Load the vrange options and hard limits
        self.ratio_var_ranges = vrange_limit_options
        self.init_table_actions = initial_point_actions
        self.var_hard_limit = vrange_hard_limit

        self.env_box.check_only_var.setChecked(True)

        # Add additional variables to table as well
        # Combine the variables from the env with the additional variables
        all_variables = {}  # note this stores the hard bounds of the variables
        try:
            additional_variables = template_dict["additional_variables"]
        except KeyError:
            additional_variables = []  # init to empty list if not present
        if self.vars_env:
            for i in self.vars_env:
                all_variables.update(i)
        if additional_variables:  # there are additional variables
            env = self.create_env()
            for vname in additional_variables:
                try:
                    bounds = env.get_bounds([vname])[vname]
                except BadgerEnvVarError as e:
                    msg = str(e)
                    bounds = eval(msg.split(": ")[1])

                all_variables.update({vname: bounds})
        # Override the hard limits with the ones from the routine
        all_variables.update(self.var_hard_limit)
        # Format for update_variables method
        all_variables = dict(sorted(all_variables.items()))
        all_variables = [{key: value} for key, value in all_variables.items()]

        self.env_box.var_table.update_variables(all_variables)
        self.env_box.var_table.set_selected(vocs.variables)
        self.env_box.var_table.addtl_vars = additional_variables

        flag_relative = relative_to_current
        self.env_box.relative_to_curr.blockSignals(True)
        self.env_box.relative_to_curr.setChecked(flag_relative)
        self.env_box.relative_to_curr.blockSignals(False)
        self.toggle_relative_to_curr(flag_relative, refresh=False)

        if env_name:
            if flag_relative:
                bounds = self.calc_auto_bounds()
                self.env_box.var_table.set_bounds(bounds, signal=False)
            else:
                self.env_box.var_table.set_bounds(vocs.variables, signal=False)
            # Populate the initial table anyways, auto mode or not
            self.clear_init_table(reset_actions=False)
            self.update_init_table(force=True)

        # set objectives
        try:
            formulas = template_dict["formulas"]
        except KeyError:
            formulas = {}

        # Initialize the objective table with env observables
        objectives = []
        for name in self.configs["observations"]:
            obj = {name: "MINIMIZE"}
            objectives.append(obj)
        self.env_box.obj_table.update_objectives(objectives)

        for name, formula in formulas.items():
            formula_tuple = (
                name,
                formula["formula"],
                formula["variable_mapping"],
            )
            self.env_box.obj_table.add_formula_objective(formula_tuple)
        self.env_box.obj_table.set_selected(vocs.objectives)
        self.env_box.obj_table.set_rules(vocs.objectives)
        self.env_box.check_only_obj.setChecked(True)

        # set constraints
        self.env_box.con_table.clear_constraints()
        constraints = vocs.constraints
        if len(constraints):
            for name, val in constraints.items():
                relation, thres = val
                critical = name in critical_constraint_names
                relation = ["GREATER_THAN", "LESS_THAN"].index(relation)
                self.add_constraint(name, relation, thres, critical)

        # set observables
        self.env_box.list_obs.clear()
        observables = vocs.observable_names
        if len(observables):
            for name_sta in observables:
                self.add_state(name_sta)

    def generate_template_dict_from_gui(self):
        """
        Generate a template dictionary from the current state of the GUI
        """

        vocs, critical_constraints = self._compose_vocs()

        # Filter generator
        generator_name = self.generator_box.cb.currentText()

        generator_config = self._filter_generator_params(
            generator_name=generator_name,
            generator_config=load_config(self.generator_box.edit.toPlainText()),
        )

        template_dict = {
            "name": self.edit_save.text(),
            "description": str(self.edit_descr.toPlainText()),
            "relative_to_current": self.env_box.relative_to_curr.isChecked(),
            "generator": {
                "name": generator_name,
            }
            | generator_config,
            "environment": {
                "name": self.env_box.cb.currentText(),
                "params": load_config(self.env_box.edit.toPlainText()),
            },
            "vrange_limit_options": self.ratio_var_ranges,
            "vrange_hard_limit": self.var_hard_limit,
            "additional_variables": self.env_box.var_table.addtl_vars,
            "formulas": self.env_box.obj_table.formulas,
            "initial_point_actions": self.init_table_actions,
            "critical_constraint_names": critical_constraints,
            "vocs": vars(vocs),
            "badger_version": get_badger_version(),
            "xopt_version": get_xopt_version(),
        }

        return template_dict

    def _filter_generator_params(self, generator_name: str, generator_config: dict):
        """
        Filter which generator parameters get saved to template
        """

        if generator_name in ["expected_improvement", "upper_confidence_bound"]:
            if (
                "turbo_controller" in generator_config
                and generator_config["turbo_controller"] is not None
                and isinstance(generator_config["turbo_controller"], dict)
            ):
                turbo = generator_config["turbo_controller"]
                generator_config["turbo_controller"] = {
                    k: v
                    for k, v in turbo.items()
                    if k
                    in {
                        "name",
                        "length",
                        "length_max",
                        "length_min",
                        "failure_tolerance",
                        "success_tolerance",
                        "scale_factor",
                        "restrict_model_data",
                    }
                }

        return generator_config

    def save_template_yaml(self):
        """
        Save the current routine as a template .yaml file
        """

        template_dict = self.generate_template_dict_from_gui()

        options = QFileDialog.Options()
        # Suggest a filename based on the routine name or placeholder
        routine_name = self.edit_save.text() or self.edit_save.placeholderText()
        if not routine_name:
            routine_name = "template_" + datetime.now().strftime("%y%m%d_%H%M%S")
        suggested_filename = f"{routine_name}.yaml"
        template_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Template",
            os.path.join(self.template_dir, suggested_filename),
            "YAML Files (*.yaml);;All Files (*)",
            options=options,
        )

        if not template_path:
            return

        try:
            with open(template_path, "w") as stream:
                yaml.dump(template_dict, stream)
                self.sig_save_template.emit(
                    f"Current routine options saved to template: {os.path.basename(template_path)}"
                )
        except (FileNotFoundError, yaml.YAMLError) as e:
            print(f"Error saving template: {e}")
            return

    def refresh_ui(self, routine: Routine = None, silent: bool = False):
        self.routine = routine  # save routine for future reference

        self.generators = list_generators()
        self.envs = list_env()
        # Clean up the constraints/observables list
        self.env_box.con_table.clear_constraints()
        self.env_box.list_obs.clear()

        if routine is None:
            # Reset the generator and env configs
            self.generator_box.cb.setCurrentIndex(-1)
            self.env_box.cb.setCurrentIndex(-1)
            init_table = self.env_box.init_table
            init_table.clear()
            init_table.horizontalHeader().setVisible(False)
            init_table.setRowCount(10)
            init_table.setColumnCount(0)

            # Reset the routine configs check box status
            self.env_box.check_only_var.setChecked(False)
            self.env_box.check_only_obj.setChecked(False)
            self.env_box.relative_to_curr.setChecked(True)
            self.try_populate_init_table()

            # Reset the save settings
            name = generate_slug(2)
            self.edit_save.setText("")
            self.edit_save.setPlaceholderText(name)
            self.edit_descr.setPlainText("")
            self.btn_descr_update.setDisabled(True)

            return

        # Enable description edition
        self.btn_descr_update.setDisabled(False)
        # Fill in the generator and env configs
        name_generator = routine.generator.name
        try:
            idx_generator = self.generators.index(name_generator)
        except ValueError as e:
            if not silent:  # show the error message if not in silent mode
                details = traceback.format_exc()
                dialog = BadgerScrollableMessageBox(
                    title="Error!", text=str(e), parent=self
                )
                dialog.setIcon(QMessageBox.Critical)
                dialog.setDetailedText(details)
                dialog.exec_()

            idx_generator = -1

        self.generator_box.cb.setCurrentIndex(idx_generator)
        # self.generator_box.edit.setPlainText(routine.generator.yaml())
        filtered_config = filter_generator_config(
            name_generator, routine.generator.model_dump()
        )
        self.generator_box.edit.setPlainText(get_yaml_string(filtered_config))
        self.script = routine.script

        name_env = routine.environment.name
        idx_env = self.envs.index(name_env)
        self.env_box.cb.setCurrentIndex(idx_env)
        env_params = routine.environment.model_dump()
        del env_params["interface"]
        self.env_box.edit.setPlainText(get_yaml_string(env_params))

        # Config the vocs panel
        variables = routine.vocs.variable_names
        self.env_box.check_only_var.setChecked(True)

        self.env_box.edit_var.clear()

        try:
            self.var_hard_limit = routine.vrange_hard_limit
        except AttributeError:
            self.var_hard_limit = {}
        # Add additional variables to table as well
        # Combine the variables from the env with the additional variables
        all_variables = {}  # note this stores the hard bounds of the variables
        for i in self.vars_env:
            all_variables.update(i)
        if routine.additional_variables:  # there are additional variables
            env = self.create_env()
            for vname in routine.additional_variables:
                try:
                    bounds = env.get_bounds([vname])[vname]
                except BadgerEnvVarError as e:
                    msg = str(e)
                    bounds = eval(msg.split(": ")[1])

                all_variables.update({vname: bounds})
        # Override the hard limits with the ones from the routine
        all_variables.update(self.var_hard_limit)
        # Format for update_variables method
        all_variables = dict(sorted(all_variables.items()))
        all_variables = [{key: value} for key, value in all_variables.items()]

        self.env_box.var_table.update_variables(all_variables)
        self.env_box.var_table.set_selected(variables)
        self.env_box.var_table.addtl_vars = routine.additional_variables

        flag_relative = routine.relative_to_current
        if flag_relative:  # load the relative to current settings
            self.ratio_var_ranges = routine.vrange_limit_options
            self.init_table_actions = routine.initial_point_actions
        self.env_box.relative_to_curr.blockSignals(True)
        self.env_box.relative_to_curr.setChecked(flag_relative)
        self.env_box.relative_to_curr.blockSignals(False)
        self.toggle_relative_to_curr(flag_relative, refresh=False)

        # Always use ranges stored in routine
        self.env_box.var_table.set_bounds(routine.vocs.variables, signal=False)

        # Fill in initial points stored in routine if available
        try:
            # Update the header
            update_init_data_table(self.env_box.init_table, variables)
            # Fill in the table
            init_points = routine.initial_points
            set_init_data_table(self.env_box.init_table, init_points)
        except KeyError:
            set_init_data_table(self.env_box.init_table, None)

        # set objectives
        try:
            formulas = routine.formulas
        except AttributeError:
            formulas = {}

        # Initialize the objective table with env observables
        objectives = []
        for name in self.configs["observations"]:
            obj = {name: "MINIMIZE"}
            objectives.append(obj)
        self.env_box.obj_table.update_objectives(objectives)

        for name, formula in formulas.items():
            formula_tuple = (
                name,
                formula["formula"],
                formula["variable_mapping"],
            )
            self.env_box.obj_table.add_formula_objective(formula_tuple)
        self.env_box.obj_table.set_selected(routine.vocs.objectives)
        self.env_box.obj_table.set_rules(routine.vocs.objectives)
        self.env_box.check_only_obj.setChecked(True)

        constraints = routine.vocs.constraints
        if len(constraints):
            for name, val in constraints.items():
                relation, thres = val
                critical = name in routine.critical_constraint_names
                relation = ["GREATER_THAN", "LESS_THAN", "EQUAL_TO"].index(relation)
                self.add_constraint(name, relation, thres, critical)

        observables = routine.vocs.observable_names
        if len(observables):
            for name_sta in observables:
                self.add_state(name_sta)

        # Config the metadata
        self.edit_save.setPlaceholderText(generate_slug(2))
        self.edit_save.setText(routine.name)
        self.edit_descr.setPlainText(routine.description)

        self.generator_box.check_use_script.setChecked(not not self.script)

    def select_generator(self, i):
        # Reset the script
        self.script = ""
        self.generator_box.check_use_script.setChecked(False)

        if i == -1:
            self.generator_box.edit.setPlainText("")
            self.generator_box.cb_scaling.setCurrentIndex(-1)
            return

        name = self.generators[i]
        default_config = get_generator_defaults(name)

        if name in all_generator_names["bo"]:
            # Patch for BOs that make the low noise prior False by default
            default_config["gp_constructor"]["use_low_noise_prior"] = False
            # Patch for BOs that turn on TuRBO by default
            # default_config["turbo_controller"] = "optimize"

        # Patch to only show part of the config
        filtered_config = filter_generator_config(name, default_config)
        self.generator_box.edit.setPlainText(get_yaml_string(filtered_config))

        # Update the docs
        self.window_docs.update_docs(name)

    def _fill_init_table(self):  # make sure self.init_table_actions is set
        for action in self.init_table_actions:
            if action["type"] == "add_curr":
                self.fill_curr_in_init_table(record=False)
            elif action["type"] == "add_rand":
                try:
                    self.add_rand_in_init_table(
                        add_rand_config=action["config"],
                        record=False,
                    )
                except IndexError:  # lower bound is the same as upper bound
                    pass

    def toggle_use_script(self):
        if self.generator_box.check_use_script.isChecked():
            self.generator_box.btn_edit_script.show()
            self.generator_box.edit.setReadOnly(True)
            self.refresh_params_generator()
        else:
            self.generator_box.btn_edit_script.hide()
            self.generator_box.edit.setReadOnly(False)

    def edit_script(self):
        generator = self.generator_box.cb.currentText()
        dlg = BadgerEditScriptDialog(self, generator, self.script, self.script_updated)
        dlg.exec()

    def script_updated(self, text):
        self.script = text
        self.refresh_params_generator()

    def create_env(self):
        env_params = load_config(self.env_box.edit.toPlainText())
        try:
            intf_name = self.configs["interface"][0]
        except KeyError:
            intf_name = None
        configs = {"params": env_params, "interface": [intf_name]}
        try:
            env = instantiate_env(self.env, configs)
        except Exception as e:
            raise BadgerEnvInstantiationError(f"Failed to instantiate environment: {e}")

        return env

    def refresh_params_generator(self):
        if not self.script:
            return

        try:
            tmp = {}
            exec(self.script, tmp)
            try:
                tmp["generate"]  # test if generate function is defined
            except Exception as e:
                QMessageBox.warning(
                    self, "Please define a valid generate function!", str(e)
                )
                return

            env = self.create_env()
            # Get vocs
            try:
                vocs = self._compose_vocs()
            except Exception:
                vocs = None
            # Function generate comes from the script
            params_generator = tmp["generate"](env, vocs)
            self.generator_box.edit.setPlainText(get_yaml_string(params_generator))
        except Exception as e:
            QMessageBox.warning(self, "Invalid script!", str(e))

    def select_env(self, i):
        # Reset the initial table actions and ratio var ranges
        self.init_table_actions = []
        self.ratio_var_ranges = {}
        self.var_hard_limit = {}

        if hasattr(self, "archive_search"):
            self.archive_search.close()

        if i == -1:
            self.env_box.edit.setPlainText("")
            self.env_box.edit_var.clear()
            self.env_box.var_table.update_variables(None)
            self.env_box.edit_obj.clear()
            self.env_box.obj_table.update_objectives(None)
            self.configs = None
            self.env = None
            self.env_box.btn_add_con.setDisabled(True)
            self.env_box.btn_add_sta.setDisabled(True)
            self.env_box.btn_add_var.setDisabled(True)
            self.env_box.btn_lim_vrange.setDisabled(True)
            self.env_box.btn_refresh.setDisabled(True)
            self.routine = None
            self.env_box.update_stylesheets()
            return

        name = self.envs[i]
        try:
            env, configs = get_env(name)
            self.configs = configs
            self.env = env
            self.env_box.edit_var.clear()
            self.env_box.edit_obj.clear()
            self.env_box.btn_add_con.setDisabled(False)
            self.env_box.btn_add_sta.setDisabled(False)
            self.env_box.btn_add_var.setDisabled(False)
            self.env_box.btn_lim_vrange.setDisabled(False)
            self.env_box.btn_refresh.setDisabled(False)
            if self.generator_box.check_use_script.isChecked():
                self.refresh_params_generator()
        except Exception:
            self.configs = None
            self.env = None
            self.env_box.cb.setCurrentIndex(-1)
            self.env_box.btn_add_con.setDisabled(True)
            self.env_box.btn_add_sta.setDisabled(True)
            self.env_box.btn_add_var.setDisabled(True)
            self.env_box.btn_lim_vrange.setDisabled(True)
            self.routine = None
            return QMessageBox.critical(self, "Error!", traceback.format_exc())

        self.env_box.edit.setPlainText(get_yaml_string(configs["params"]))

        # Get and save vars to combine with additional vars added on the fly
        vars_env = self.vars_env = configs["variables"]
        vars_combine = [*vars_env]

        self.env_box.check_only_var.blockSignals(True)
        self.env_box.check_only_var.setChecked(False)
        self.env_box.var_table.checked_only = False  # reset the checked only flag
        self.env_box.check_only_var.blockSignals(False)
        self.env_box.var_table.update_variables(vars_combine)
        # Auto apply the limited variable ranges if the option is set
        if self.env_box.relative_to_curr.isChecked():
            self.set_vrange()

        # Needed for getting bounds on the fly
        self.env_box.var_table.env_class, self.env_box.var_table.configs = (
            self.add_var()
        )

        _objs_env = configs["observations"]
        objs_env = []
        for name in _objs_env:
            obj = {}
            obj[name] = "MINIMIZE"  # default rule
            objs_env.append(obj)
        self.env_box.check_only_obj.setChecked(False)
        self.env_box.obj_table.update_objectives(objs_env)

        self.env_box.con_table.clear_constraints()
        self.env_box.list_obs.clear()
        self.env_box.fit_content()
        # self.routine = None

        self.env_box.update_stylesheets(env.name)

        # Update the docs
        self.window_env_docs.update_docs(env.name)

    def get_init_table_header(self):
        table = self.env_box.init_table
        header_list = []
        for col in range(table.columnCount()):
            item = table.horizontalHeaderItem(col)
            if item:
                header_list.append(item.text())
            else:
                header_list.append("")  # Handle the case where the header item is None
        return header_list

    def fill_curr_in_init_table(self, record=False):
        env = self.create_env()
        table = self.env_box.init_table
        vname_selected = self.get_init_table_header()

        try:
            # Get the current variables from the environment
            var_curr = env.get_variables(vname_selected)
        except Exception as e:
            raise BadgerEnvVarError(
                f"Failed to get current variable values : {e}\n"
                "Please ensure the environment is properly configured."
            )

        # Iterate through the rows
        for row in range(table.rowCount()):
            # Check if the row is empty
            if np.all(
                [not table.item(row, col).text() for col in range(table.columnCount())]
            ):
                # Fill the row with content_list
                for col, name in enumerate(vname_selected):
                    item = QTableWidgetItem(f"{var_curr[name]:.4g}")
                    table.setItem(row, col, item)
                break  # Stop after filling the first non-empty row

        if record and self.env_box.relative_to_curr.isChecked():
            self.init_table_actions.append({"type": "add_curr"})

    def save_add_rand_config(self, add_rand_config):
        self.add_rand_config = add_rand_config

    def add_rand_in_init_table(self, add_rand_config=None, record=True):
        if add_rand_config is None:
            add_rand_config = self.add_rand_config

        # Get current point
        env = self.create_env()
        vname_selected = self.get_init_table_header()
        var_curr = env.get_variables(vname_selected)

        # get small region around current point to sample
        try:
            vocs, _ = self._compose_vocs()
        except Exception:
            # Switch to manual mode to allow the user fixing the vocs issue
            QMessageBox.warning(
                self,
                "Variable range is not valid!",
                "Auto mode disabled due to invalid variable range. Please fix it before enabling auto mode.",
            )
            return self.env_box.relative_to_curr.setChecked(False)

        n_point = add_rand_config["n_points"]
        fraction = add_rand_config["fraction"]
        random_sample_region = get_local_region(var_curr, vocs, fraction=fraction)
        with warnings.catch_warnings(record=True) as caught_warnings:
            try:
                random_points = vocs.random_inputs(
                    n_point, custom_bounds=random_sample_region
                )
            except ValueError:
                raise VariableRangeError(
                    "Current value is not within variable range!\n"
                    "This is likely due to the hard variable bounds being overridden, "
                    "please examine the individual variable settings."
                )

            for warning in caught_warnings:
                # Ignore runtime warnings (usually caused by clip by bounds)
                if warning.category is RuntimeWarning:
                    pass
                else:
                    print(f"Caught user warning: {warning.message}")

        # Add points to the table
        table = self.env_box.init_table
        for row in range(table.rowCount()):
            # Check if the row is empty
            if np.all(
                [not table.item(row, col).text() for col in range(table.columnCount())]
            ):
                # Fill the row with content_list
                try:
                    point = random_points.pop(0)
                    for col, name in enumerate(vname_selected):
                        item = QTableWidgetItem(f"{point[name]:.4g}")
                        table.setItem(row, col, item)
                except IndexError:  # No more points to add
                    break

        if record and self.env_box.relative_to_curr.isChecked():
            self.init_table_actions.append(
                {
                    "type": "add_rand",
                    "config": add_rand_config,
                }
            )

    def show_add_rand_dialog(self):
        dlg = BadgerAddRandomDialog(
            self,
            self.add_rand_in_init_table,
            self.save_add_rand_config,
            self.add_rand_config,
        )
        self.rc_dialog = dlg
        try:
            dlg.exec()
        finally:
            self.rc_dialog = None

    def clear_init_table(self, reset_actions=True):
        table = self.env_box.init_table
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item:
                    item.setText("")  # Set the cell content to an empty string

        if reset_actions and self.env_box.relative_to_curr.isChecked():
            self.init_table_actions = []  # reset the recorded actions

    def add_row_to_init_table(self):
        table = self.env_box.init_table
        row_position = table.rowCount()
        table.insertRow(row_position)

        for col in range(table.columnCount()):
            item = QTableWidgetItem("")
            table.setItem(row_position, col, item)

    def open_playground(self):
        pass

    def open_generator_docs(self):
        self.window_docs.show()

    def open_environment_docs(self):
        self.window_env_docs.show()

    def open_archive_search(self):
        if not hasattr(self, "archive_search") or not self.archive_search.isVisible():
            try:
                env = self.create_env()
            except AttributeError:
                raise BadgerRoutineError("No environment selected!")

            self.archive_search = ArchiveSearchWidget(environment=env)
            self.archive_search.show()
        else:
            self.archive_search.raise_()
            self.archive_search.activateWindow()

    def add_var(self):
        # TODO: Use a cached env
        env_params = load_config(self.env_box.edit.toPlainText())
        try:
            intf_name = self.configs["interface"][0]
        except KeyError:
            intf_name = None
        configs = {"params": env_params, "interface": [intf_name]}

        return self.env, configs
        # dlg = BadgerVariableDialog(self, self.env, configs, self.add_var_to_list)
        # dlg.exec()

    def limit_variable_ranges(self):
        if self.lim_apply_to_vars == 2:
            # Initialize the lim_apply_to_vars to 0 (set only visible vars)
            self.lim_apply_to_vars = 0

        dlg = BadgerLimitVariableRangeDialog(
            self,
            self.set_vrange,
            self.save_limit_option,
            self.limit_option,
            self.lim_apply_to_vars,
        )
        dlg.exec()

    def set_vrange(self, set_all=True):
        # By default update all variables no matter if selected or not
        vname_selected = []
        vrange = {}

        if set_all:
            # Set vranges for all variables
            _variables = self.env_box.var_table.all_variables
        else:
            # Only set vranges for the visible variables
            _variables = self.env_box.var_table.get_visible_variables(
                self.env_box.var_table.variables
            )

        for var in _variables:
            name = next(iter(var))
            # Set vrange no matter if selected or not
            # if set_all or self.env_box.var_table.is_checked(name):
            vname_selected.append(name)
            vrange[name] = var[name]

        env = self.create_env()
        try:
            # Get the current variables from the environment
            var_curr = env.get_variables(vname_selected)
        except Exception as e:
            raise BadgerEnvVarError(
                f"Failed to get current variable values : {e}\n"
                "Please ensure the environment is properly configured."
            )

        option_idx = self.limit_option["limit_option_idx"]
        # 0: ratio with current value, 1: ratio with full range, 2: delta around current value
        if option_idx == 1:
            ratio = self.limit_option["ratio_full"]
            for i, name in enumerate(vname_selected):
                hard_bounds = vrange[name]
                delta = 0.5 * ratio * (hard_bounds[1] - hard_bounds[0])
                bounds = [var_curr[name] - delta, var_curr[name] + delta]
                bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
                vrange[name] = bounds
        elif option_idx == 2:
            delta = self.limit_option["delta"]
            for i, name in enumerate(vname_selected):
                hard_bounds = vrange[name]
                bounds = [var_curr[name] - delta, var_curr[name] + delta]
                bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
                vrange[name] = bounds
        else:
            ratio = self.limit_option["ratio_curr"]
            for i, name in enumerate(vname_selected):
                hard_bounds = vrange[name]
                sign = np.sign(var_curr[name])
                bounds = [
                    var_curr[name] * (1 - 0.5 * sign * ratio),
                    var_curr[name] * (1 + 0.5 * sign * ratio),
                ]
                bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
                vrange[name] = bounds

        self.env_box.var_table.set_bounds(vrange)
        self.clear_init_table(reset_actions=False)  # clear table after changing ranges
        self.update_init_table()  # auto populate if option is set

        # remember user selection for applying limit changes
        if not self.lim_apply_to_vars == 2:
            # Check if lim_apply_to_vars has been initialized
            # It will be set to 2 until the btn_lim_vrange is clicked
            self.lim_apply_to_vars = set_all

        # Record the ratio var ranges
        for vname in vname_selected:
            self.ratio_var_ranges[vname] = copy.deepcopy(self.limit_option)

    def set_ind_vrange(self, vname, config):
        hard_bounds = [config["lower_bound"], config["upper_bound"]]
        option = {
            "limit_option_idx": config["limit_option_idx"],
            "ratio_full": config["ratio_full"],
            "ratio_curr": config["ratio_curr"],
            "delta": config["delta"],
        }

        option_idx = option["limit_option_idx"]

        env = self.create_env()
        curr = env.get_variables([vname])[vname]

        # 0: ratio with current value, 1: ratio with full range, 2: delta around current value
        if option_idx == 1:
            ratio = option["ratio_full"]
            delta = 0.5 * ratio * (hard_bounds[1] - hard_bounds[0])
            bounds = [curr - delta, curr + delta]
            bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
        elif option_idx == 2:
            delta = option["delta"]
            bounds = [curr - delta, curr + delta]
            bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
        else:
            ratio = option["ratio_curr"]
            sign = np.sign(curr)
            bounds = [
                curr * (1 - 0.5 * sign * ratio),
                curr * (1 + 0.5 * sign * ratio),
            ]
            bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()

        # Set the bounds in the table
        self.env_box.var_table.refresh_variable(vname, bounds, hard_bounds)
        self.clear_init_table(reset_actions=False)  # clear table after changing ranges
        self.update_init_table()  # auto populate if option is set

        # Record the hard bounds for the variable
        self.var_hard_limit[vname] = hard_bounds
        # Record the ratio var ranges
        self.ratio_var_ranges[vname] = copy.deepcopy(option)

    def save_limit_option(self, limit_option):
        self.limit_option = limit_option

    def add_var_to_list(self, name, lb, ub):
        # Check if already in the list
        ok = False
        try:
            self.env_box.var_table.bounds[name]
        except KeyError:
            ok = True
        if not ok:
            QMessageBox.warning(
                self, "Variable already exists!", f"Variable {name} already exists!"
            )
            return 1

        self.env_box.add_var(name, lb, ub)
        return 0

    def update_init_table(self, force=False):
        selected = self.env_box.var_table.selected
        variable_names = [v for v in selected if selected[v]]
        update_init_data_table(self.env_box.init_table, variable_names)

        if (not force) and (not self.env_box.relative_to_curr.isChecked()):
            return

        # Auto populate the initial table based on recorded actions
        if not self.init_table_actions:
            self.init_table_actions = [
                {"type": "add_curr"},
                {"type": "add_rand", "config": self.add_rand_config},
            ]
        self.clear_init_table(reset_actions=False)
        self._fill_init_table()

    def calc_auto_bounds(self):
        vname_selected = []
        vrange = {}

        for var in self.env_box.var_table.variables:
            name = next(iter(var))
            vname_selected.append(name)
            try:  # get the hard limit from the routine
                vrange[name] = self.var_hard_limit[name]
            except KeyError:
                vrange[name] = var[name]

        env = self.create_env()
        var_curr = env.get_variables(vname_selected)

        for name in vname_selected:
            try:
                limit_option = self.ratio_var_ranges[name]
            except KeyError:
                limit_option = self.limit_option

            option_idx = limit_option["limit_option_idx"]
            # 0: ratio with current value, 1: ratio with full range, 2: delta around current value
            if option_idx == 1:
                ratio = limit_option["ratio_full"]
                hard_bounds = vrange[name]
                delta = 0.5 * ratio * (hard_bounds[1] - hard_bounds[0])
                bounds = [var_curr[name] - delta, var_curr[name] + delta]
                bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
                vrange[name] = bounds
            elif option_idx == 2:
                delta = limit_option["delta"]
                hard_bounds = vrange[name]
                bounds = [var_curr[name] - delta, var_curr[name] + delta]
                bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
                vrange[name] = bounds
            else:
                ratio = limit_option["ratio_curr"]
                hard_bounds = vrange[name]
                sign = np.sign(var_curr[name])
                bounds = [
                    var_curr[name] * (1 - 0.5 * sign * ratio),
                    var_curr[name] * (1 + 0.5 * sign * ratio),
                ]
                bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
                vrange[name] = bounds

        return vrange

    def toggle_relative_to_curr(self, checked, refresh=True):
        if checked:
            try:
                _ = self._compose_vocs()
            except Exception:
                # Switch to manual mode to allow the user fixing the vocs issue
                # Schedule the checkbox to be clicked after the event loop finishes
                QTimer.singleShot(0, lambda: self.env_box.relative_to_curr.click())
                QMessageBox.warning(
                    self,
                    "Variable range is not valid!",
                    "Please fix the invalid variable range before enabling auto mode.",
                )
                return

            self.env_box.switch_var_panel_style(True)

            if refresh and self.env_box.var_table.selected:
                bounds = self.calc_auto_bounds()
                self.env_box.var_table.set_bounds(bounds)
                self.clear_init_table(reset_actions=False)
                # Auto populate the initial table
                self.try_populate_init_table()

            self.env_box.var_table.lock_bounds()
            self.env_box.init_table.set_uneditable()
        else:
            self.env_box.switch_var_panel_style(False)

            self.env_box.var_table.unlock_bounds()
            self.env_box.init_table.set_editable()

    def refresh_variables(self):
        variables = self.env_box.var_table.export_variables()
        bounds = self.calc_auto_bounds()

        no_need_to_update = True
        for vname in variables:
            if not np.allclose(bounds[vname], variables[vname]):
                no_need_to_update = False
                break
        if no_need_to_update:
            return

        self.env_box.var_table.set_bounds(bounds)
        self.clear_init_table(reset_actions=False)
        self.try_populate_init_table()

    def try_populate_init_table(self):
        if (
            self.env_box.relative_to_curr.isChecked()
            and self.env_box.var_table.selected
        ):
            self.update_init_table()

    def handle_pv_added(self):
        if self.env_box.relative_to_curr.isChecked():
            self.set_vrange()

    def handle_var_config(self, vname):
        env = self.create_env()
        curr = env.get_variables([vname])[vname]

        # Get the hard limit
        try:
            bounds = self.var_hard_limit[vname]
        except KeyError:
            try:
                bounds = env.get_bounds([vname])[vname]
            except BadgerEnvVarError as e:
                msg = str(e)
                bounds = eval(msg.split(": ")[1])

        # Get the option
        try:
            option = self.ratio_var_ranges[vname]
        except KeyError:
            option = self.limit_option

        configs = {
            "current_value": curr,
            "lower_bound": bounds[0],
            "upper_bound": bounds[1],
            **option,
        }

        BadgerIndividualLimitVariableRangeDialog(
            self,
            vname,
            self.set_ind_vrange,
            configs,
        ).exec_()

    def add_constraint(self, name=None, relation=0, threshold=0, critical=False):
        if self.configs is None:
            return

        options = self.configs["observations"]
        self.env_box.con_table.add_constraint(
            options,
            name,
            relation,
            threshold,
            critical,
        )

    def add_state(self, name=None):
        if self.configs is None:
            return

        var_names = [next(iter(d)) for d in self.configs["variables"]]
        options = self.configs["observations"] + var_names
        item = QListWidgetItem(self.env_box.list_obs)
        sta_item = state_item(
            options,
            lambda: self.env_box.list_obs.takeItem(self.env_box.list_obs.row(item)),
            name,
        )
        item.setSizeHint(sta_item.sizeHint())
        self.env_box.list_obs.addItem(item)
        self.env_box.list_obs.setItemWidget(item, sta_item)
        self.env_box.fit_content()

    def _compose_vocs(self) -> (VOCS, list[str]):
        # Compose the VOCS settings
        variables = self.env_box.var_table.export_variables()
        objectives = self.env_box.obj_table.export_objectives()

        constraints = {}
        critical_constraints = []
        for (
            con_name,
            relation,
            threshold,
            critical,
            _,
        ) in self.env_box.con_table.export_constraints():
            constraints[con_name] = [relation, threshold]
            if critical:
                critical_constraints.append(con_name)

        observables = []
        for i in range(self.env_box.list_obs.count()):
            item = self.env_box.list_obs.item(i)
            item_widget = self.env_box.list_obs.itemWidget(item)
            obs_name = item_widget.cb_sta.currentText()
            observables.append(obs_name)

        try:
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

    def _compose_routine(self) -> Routine:
        # Compose the routine
        # Metadata
        name = self.edit_save.text() or self.edit_save.placeholderText()
        description = self.edit_descr.toPlainText()

        # General sanity checks
        if self.generator_box.cb.currentIndex() == -1:
            raise BadgerRoutineError("no generator selected")
        if self.env_box.cb.currentIndex() == -1:
            raise BadgerRoutineError("no environment selected")

        # Generator
        generator_name = self.generators[self.generator_box.cb.currentIndex()]
        env_name = self.envs[self.env_box.cb.currentIndex()]
        generator_params = load_config(self.generator_box.edit.toPlainText())
        if generator_name in all_generator_names["bo"]:
            # Patch the BO generators to make sure use_low_noise_prior is False
            if "gp_constructor" not in generator_params:
                generator_params["gp_constructor"] = {
                    "name": "standard",  # have to add name too for pydantic validation
                    "use_low_noise_prior": False,
                }
            # or else we use whatever specified by the users

            if generator_name != "mobo":
                # Patch the BO generators to turn on TuRBO by default
                if "turbo_controller" not in generator_params:
                    generator_params["turbo_controller"] = "optimize"

                # TODO: remove this patch when Xopt reset API works
                # Nullify a few properties in turbo that can cause issues
                turbo_config = generator_params["turbo_controller"]
                if type(turbo_config) is dict:
                    if turbo_config["name"] == "optimize":
                        turbo_config["center_x"] = None
                        turbo_config["best_value"] = None
                    elif turbo_config["name"] == "safety":
                        turbo_config["center_x"] = None

        # Environment
        env_params = load_config(self.env_box.edit.toPlainText())

        # VOCS
        vocs, critical_constraints = self._compose_vocs()
        if not vocs.variables:
            raise BadgerRoutineError("no variables selected")
        if not vocs.objectives:
            raise BadgerRoutineError("no objectives selected")

        # Initial points
        init_points_df = pd.DataFrame.from_dict(
            get_table_content_as_dict(self.env_box.init_table)
        )
        init_points_df = init_points_df.replace("", pd.NA)
        init_points_df = init_points_df.dropna(subset=init_points_df.columns, how="all")
        if init_points_df.empty:
            raise BadgerRoutineError(
                "No initial points provided. Please add at least one initial point"
            )
        contains_na = init_points_df.isna().any().any()
        if contains_na:
            raise BadgerRoutineError(
                "Initial points are not valid, please fill in the missing values"
            )

        # Script that generates generator params
        if self.generator_box.check_use_script.isChecked():
            script = self.script
        else:
            script = None

        # Relative to current params
        if self.env_box.relative_to_curr.isChecked():
            relative_to_current = True
            vrange_limit_options = self.ratio_var_ranges
            initial_point_actions = self.init_table_actions
        else:
            relative_to_current = False
            vrange_limit_options = None
            initial_point_actions = None

        # Save hard limits no matter relative to current or not
        vrange_hard_limit = self.var_hard_limit

        try:
            generator = get_generator_dynamic(generator_name)(
                vocs=vocs, **generator_params
            )
        except ValidationError as e:
            raise BadgerRoutineError(
                f"\n\nAlgorithm validation failed: {format_validation_error(e)}"
            ) from e

        with warnings.catch_warnings(record=True) as caught_warnings:
            routine = Routine(
                # Metadata
                badger_version=get_badger_version(),
                xopt_version=get_xopt_version(),
                # Xopt part
                vocs=vocs,
                generator=generator,
                # Badger part
                name=name,
                description=description,
                environment={"name": env_name} | env_params,
                initial_points=init_points_df.astype("double"),
                critical_constraint_names=critical_constraints,
                tags=None,
                script=script,
                relative_to_current=relative_to_current,
                vrange_limit_options=vrange_limit_options,
                vrange_hard_limit=vrange_hard_limit,
                initial_point_actions=initial_point_actions,
                additional_variables=self.env_box.var_table.addtl_vars,
                formulas=self.env_box.obj_table.formulas,
            )

            # Check if any user warnings were caught
            for warning in caught_warnings:
                if issubclass(warning.category, UserWarning):
                    QMessageBox.warning(
                        self,
                        "Warning!",
                        f"Warning: {warning.message}",
                    )
                else:
                    print(f"Caught warning: {warning.message}")

            return routine

    def review(self):
        try:
            routine = self._compose_routine()
        except Exception:
            return QMessageBox.critical(
                self, "Invalid routine!", traceback.format_exc()
            )

        dlg = BadgerReviewDialog(self, routine)
        dlg.exec()

    def update_description(self):
        routine = self.routine
        routine.description = self.edit_descr.toPlainText()
        try:
            update_run(routine)
            # Notify routine list to update
            self.sig_updated.emit(routine.name, routine.description)
            QMessageBox.information(
                self,
                "Update success!",
                f"Routine {self.routine.name} description was updated!",
            )
        except Exception:
            return QMessageBox.critical(self, "Update failed!", traceback.format_exc())
