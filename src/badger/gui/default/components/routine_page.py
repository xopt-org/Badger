import json
import warnings
import sqlite3
import traceback
import copy
from functools import partial
import os
import yaml

import numpy as np
import pandas as pd
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QGroupBox, QLineEdit, QLabel, QPushButton
from PyQt5.QtWidgets import QListWidgetItem, QMessageBox, QWidget
from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QTableWidgetItem, QPlainTextEdit, QSizePolicy
from coolname import generate_slug
from pydantic import ValidationError
from xopt import VOCS
from xopt.generators import get_generator_defaults, all_generator_names
from xopt.utils import get_local_region

from badger.gui.default.components.generator_cbox import BadgerAlgoBox
from badger.gui.default.components.constraint_item import constraint_item
from badger.gui.default.components.data_table import (
    get_table_content_as_dict,
    set_init_data_table,
    update_init_data_table,
)
from badger.gui.default.components.env_cbox import BadgerEnvBox
from badger.gui.default.components.filter_cbox import BadgerFilterBox
from badger.gui.default.components.state_item import state_item
from badger.gui.default.windows.docs_window import BadgerDocsWindow
from badger.gui.default.windows.env_docs_window import BadgerEnvDocsWindow
from badger.gui.default.windows.edit_script_dialog import BadgerEditScriptDialog
from badger.gui.default.windows.lim_vrange_dialog import BadgerLimitVariableRangeDialog
from badger.gui.default.windows.review_dialog import BadgerReviewDialog
from badger.gui.default.windows.add_random_dialog import BadgerAddRandomDialog
from badger.gui.default.windows.message_dialog import BadgerScrollableMessageBox
from badger.gui.default.windows.expandable_message_box import ExpandableMessageBox
from badger.gui.default.utils import filter_generator_config
from badger.db import save_routine, update_routine, get_runs_by_routine
from badger.environment import instantiate_env
from badger.errors import BadgerRoutineError
from badger.factory import list_generators, list_env, get_env
from badger.routine import Routine
from badger.settings import init_settings
from badger.utils import (
    get_yaml_string,
    load_config,
    strtobool,
    get_badger_version,
    get_xopt_version,
)

CONS_RELATION_DICT = {
    ">": "GREATER_THAN",
    "<": "LESS_THAN",
    "=": "EQUAL_TO",
}


class BadgerRoutinePage(QWidget):
    sig_updated = pyqtSignal(str, str)  # routine name, routine description

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

        self.init_ui()
        self.config_logic()

    def init_ui(self):
        config_singleton = init_settings()

        # Set up the layout
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(11, 11, 19, 11)

        # Meta group
        group_meta = QGroupBox("Metadata")
        group_meta.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        vbox_meta = QVBoxLayout(group_meta)

        # Name
        name = QWidget()
        hbox_name = QHBoxLayout(name)
        hbox_name.setContentsMargins(0, 0, 0, 0)
        label = QLabel("Name")
        label.setFixedWidth(64)
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
        lbl_descr = QLabel("Descr")
        lbl_descr.setFixedWidth(64)
        vbox_lbl_descr.addWidget(lbl_descr)
        vbox_lbl_descr.addStretch(1)
        hbox_descr.addWidget(lbl_descr_col)

        edit_descr_col = QWidget()
        vbox_descr_edit = QVBoxLayout(edit_descr_col)
        vbox_descr_edit.setContentsMargins(0, 0, 0, 0)
        self.edit_descr = edit_descr = QPlainTextEdit()
        edit_descr.setMaximumHeight(80)
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

        # Tags
        self.cbox_tags = cbox_tags = BadgerFilterBox(title=" Tags")
        if not strtobool(config_singleton.read_value("BADGER_ENABLE_ADVANCED")):
            cbox_tags.hide()
        vbox_meta.addWidget(cbox_tags, alignment=Qt.AlignTop)
        # vbox_meta.addStretch()

        vbox.addWidget(group_meta)

        # Algo box
        self.generator_box = BadgerAlgoBox(None, self.generators)
        self.generator_box.expand()  # expand the box initially
        vbox.addWidget(self.generator_box)

        # Env box
        BADGER_PLUGIN_ROOT = config_singleton.read_value("BADGER_PLUGIN_ROOT")
        env_dict_dir = os.path.join(
            BADGER_PLUGIN_ROOT, "environments", "env_colors.yaml"
        )
        try:
            with open(env_dict_dir, "r") as stream:
                env_dict = yaml.safe_load(stream)
        except (FileNotFoundError, yaml.YAMLError):
            env_dict = {}
        self.env_box = BadgerEnvBox(env_dict, None, self.envs)
        self.env_box.expand()  # expand the box initially
        vbox.addWidget(self.env_box)

        vbox.addStretch()

    def config_logic(self):
        self.btn_descr_update.clicked.connect(self.update_description)
        self.generator_box.cb.currentIndexChanged.connect(self.select_generator)
        self.generator_box.btn_docs.clicked.connect(self.open_generator_docs)
        self.generator_box.check_use_script.stateChanged.connect(self.toggle_use_script)
        self.generator_box.btn_edit_script.clicked.connect(self.edit_script)
        self.env_box.cb.currentIndexChanged.connect(self.select_env)
        self.env_box.btn_env_play.clicked.connect(self.open_playground)
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
        self.env_box.var_table.sig_sel_changed.connect(self.update_init_table)
        self.env_box.var_table.sig_pv_added.connect(self.handle_pv_added)

    def refresh_ui(self, routine: Routine = None, silent: bool = False):
        self.routine = routine  # save routine for future reference

        self.generators = list_generators()
        self.envs = list_env()
        # Clean up the constraints/observables list
        self.env_box.list_con.clear()
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

        # Add additional variables to table as well
        # Combine the variables from the env with the additional variables
        all_variables = {}  # note this stores the hard bounds of the variables
        for i in self.vars_env:
            all_variables.update(i)
        if routine.additional_variables:  # there are additional variables
            env = self.create_env()
            # Have to check each variable since some could fail
            for v in routine.additional_variables:
                try:
                    b = env.get_bound(v)
                except Exception:
                    b = [-1000, 1000]  # default wide range
                all_variables.update({v: b})
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
            init_points = routine.initial_points
            set_init_data_table(self.env_box.init_table, init_points)
        except KeyError:
            set_init_data_table(self.env_box.init_table, None)

        objectives = routine.vocs.objective_names
        self.env_box.check_only_obj.setChecked(True)
        self.env_box.edit_obj.clear()
        self.env_box.obj_table.set_selected(objectives)
        self.env_box.obj_table.set_rules(routine.vocs.objectives)

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
            default_config["turbo_controller"] = "optimize"

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
        env = instantiate_env(self.env, configs)

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
        self.env_box.check_only_var.blockSignals(False)
        self.env_box.var_table.update_variables(vars_combine)
        # Auto apply the limited variable ranges if the option is set
        if self.env_box.relative_to_curr.isChecked():
            self.set_vrange(set_all=True)

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

        self.env_box.list_con.clear()
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
        var_curr = env._get_variables(vname_selected)

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
        var_curr = env._get_variables(vname_selected)

        # get small region around current point to sample
        vocs, _ = self._compose_vocs()
        n_point = add_rand_config["n_points"]
        fraction = add_rand_config["fraction"]
        random_sample_region = get_local_region(var_curr, vocs, fraction=fraction)
        with warnings.catch_warnings(record=True) as caught_warnings:
            random_points = vocs.random_inputs(
                n_point, custom_bounds=random_sample_region
            )

            for warning in caught_warnings:
                # Ignore runtime warnings (usually caused by clip by bounds)
                if isinstance(warning.category, RuntimeWarning):
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
        dlg = BadgerLimitVariableRangeDialog(
            self,
            self.set_vrange,
            self.save_limit_option,
            self.limit_option,
        )
        dlg.exec()

    def set_vrange(self, set_all=False):
        vname_selected = []
        vrange = {}

        for var in self.env_box.var_table.variables:
            name = next(iter(var))
            if set_all or self.env_box.var_table.is_checked(name):
                vname_selected.append(name)
                vrange[name] = var[name]

        env = self.create_env()
        var_curr = env._get_variables(vname_selected)

        option_idx = self.limit_option["limit_option_idx"]
        if option_idx:
            ratio = self.limit_option["ratio_full"]
            for i, name in enumerate(vname_selected):
                hard_bounds = vrange[name]
                delta = 0.5 * ratio * (hard_bounds[1] - hard_bounds[0])
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

        # Record the ratio var ranges
        if self.env_box.relative_to_curr.isChecked():
            for vname in vname_selected:
                self.ratio_var_ranges[vname] = copy.deepcopy(self.limit_option)

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

    def update_init_table(self):
        selected = self.env_box.var_table.selected
        variable_names = [v for v in selected if selected[v]]
        update_init_data_table(self.env_box.init_table, variable_names)

        if not self.env_box.relative_to_curr.isChecked():
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
            vrange[name] = var[name]

        env = self.create_env()
        var_curr = env._get_variables(vname_selected)

        for name in vname_selected:
            try:
                limit_option = self.ratio_var_ranges[name]
            except KeyError:
                limit_option = self.limit_option

            option_idx = limit_option["limit_option_idx"]
            if option_idx:
                ratio = limit_option["ratio_full"]
                hard_bounds = vrange[name]
                delta = 0.5 * ratio * (hard_bounds[1] - hard_bounds[0])
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

    def try_populate_init_table(self):
        if (
            self.env_box.relative_to_curr.isChecked()
            and self.env_box.var_table.selected
        ):
            self.update_init_table()

    def handle_pv_added(self):
        if self.env_box.relative_to_curr.isChecked():
            self.set_vrange()

    def add_constraint(self, name=None, relation=0, threshold=0, critical=False):
        if self.configs is None:
            return

        options = self.configs["observations"]
        item = QListWidgetItem(self.env_box.list_con)
        con_item = constraint_item(
            options,
            lambda: self.env_box.list_con.takeItem(self.env_box.list_con.row(item)),
            name,
            relation,
            threshold,
            critical,
        )
        item.setSizeHint(con_item.sizeHint())
        self.env_box.list_con.addItem(item)
        self.env_box.list_con.setItemWidget(item, con_item)
        # self.env_box.dict_con[''] = item
        self.env_box.fit_content()

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
        for i in range(self.env_box.list_con.count()):
            item = self.env_box.list_con.item(i)
            item_widget = self.env_box.list_con.itemWidget(item)
            critical = item_widget.check_crit.isChecked()
            con_name = item_widget.cb_obs.currentText()
            relation = CONS_RELATION_DICT[item_widget.cb_rel.currentText()]
            value = item_widget.sb.value()
            constraints[con_name] = [relation, value]
            if critical:
                critical_constraints.append(con_name)

        observables = []
        for i in range(self.env_box.list_obs.count()):
            item = self.env_box.list_obs.item(i)
            item_widget = self.env_box.list_obs.itemWidget(item)
            obs_name = item_widget.cb_sta.currentText()
            observables.append(obs_name)

        vocs = VOCS(
            variables=variables,
            objectives=objectives,
            constraints=constraints,
            constants={},
            observables=observables,
        )

        return vocs, critical_constraints

    def _compose_routine(self) -> Routine:
        # Compose the routine
        name = self.edit_save.text() or self.edit_save.placeholderText()
        description = self.edit_descr.toPlainText()

        if self.generator_box.cb.currentIndex() == -1:
            raise BadgerRoutineError("no generator selected")
        if self.env_box.cb.currentIndex() == -1:
            raise BadgerRoutineError("no environment selected")

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

            # Patch the BO generators to turn on TuRBO by default
            if "turbo_controller" not in generator_params:
                generator_params["turbo_controller"] = "optimize"
        env_params = load_config(self.env_box.edit.toPlainText())

        # VOCS
        vocs, critical_constraints = self._compose_vocs()

        # Initial points
        init_points_df = pd.DataFrame.from_dict(
            get_table_content_as_dict(self.env_box.init_table)
        )
        init_points_df = init_points_df.replace("", pd.NA)
        init_points_df = init_points_df.dropna(subset=init_points_df.columns, how="all")
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

        with warnings.catch_warnings(record=True) as caught_warnings:
            routine = Routine(
                # Metadata
                badger_version=get_badger_version(),
                xopt_version=get_xopt_version(),
                # Xopt part
                vocs=vocs,
                generator={"name": generator_name} | generator_params,
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
                initial_point_actions=initial_point_actions,
                additional_variables=self.env_box.var_table.addtl_vars,
            )

            # Check if any user warnings were caught
            for warning in caught_warnings:
                if isinstance(warning.category, UserWarning):
                    pass
                else:
                    print(f"Caught user warning: {warning.message}")

            return routine

    def review(self):
        try:
            routine = self._compose_routine()
        except:
            return QMessageBox.critical(
                self, "Invalid routine!", traceback.format_exc()
            )

        dlg = BadgerReviewDialog(self, routine)
        dlg.exec()

    def update_description(self):
        routine = self.routine
        routine.description = self.edit_descr.toPlainText()
        try:
            update_routine(routine)
            # Notify routine list to update
            self.sig_updated.emit(routine.name, routine.description)
            QMessageBox.information(
                self,
                "Update success!",
                f"Routine {self.routine.name} description was updated!",
            )
        except Exception:
            return QMessageBox.critical(self, "Update failed!", traceback.format_exc())

    def save(self):
        try:
            routine = self._compose_routine()
        except ValidationError as e:
            error_message = "".join(
                [error["msg"] + "\n\n" for error in e.errors()]
            ).strip()
            details = traceback.format_exc()
            dialog = ExpandableMessageBox(
                title="Error!", text=error_message, detailedText=details, parent=self
            )
            dialog.setIcon(QMessageBox.Critical)
            dialog.exec_()
            return

        try:
            if self.routine:
                keys_to_exclude = ["data", "id", "name", "description"]
                old_dict = json.loads(self.routine.json())
                old_dict = {
                    k: v for k, v in old_dict.items() if k not in keys_to_exclude
                }
                new_dict = json.loads(routine.json())
                new_dict = {
                    k: v for k, v in new_dict.items() if k not in keys_to_exclude
                }
                runs = get_runs_by_routine(self.routine.id)
                if len(runs) == 0 or old_dict == new_dict:
                    routine.id = self.routine.id
                    update_routine(routine)
                else:
                    save_routine(routine)
            else:
                save_routine(routine)
        except sqlite3.IntegrityError:
            return QMessageBox.critical(
                self,
                "Error!",
                f"Routine {routine.name} already existed in the database! Please "
                f"choose another name.",
            )

        return 0
