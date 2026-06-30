"""
Builds and edits a Routine in the mini GUI.

BadgerRoutinePage owns the environment/VOCS editor, template load/save,
variable range controls, and initial-point tools. Its main job is
_compose_routine(), which validates GUI state and returns a Routine ready
to run. It also supports the reverse path (refresh_ui/set_routine) to load
an existing Routine back into the form.
"""

from typing import Any
import warnings
import traceback
import copy
from functools import partial
import os
import yaml

import numpy as np
import pandas as pd
from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5.QtWidgets import QLineEdit, QPushButton, QFileDialog
from PyQt5.QtWidgets import QMessageBox, QWidget, QTabWidget
from PyQt5.QtWidgets import QVBoxLayout, QScrollArea
from PyQt5.QtWidgets import QTableWidgetItem, QPlainTextEdit
from badger.gui.components.navigators import HistoryNavigator
from coolname import generate_slug
from xopt import VOCS
from xopt.vocs import random_inputs
from xopt.generators import (
    get_generator_defaults,
    all_generator_names,
    get_generator_dynamic,
)
from xopt.utils import get_local_region
from gest_api.vocs import (
    BaseObjective,
    GreaterThanConstraint,
    LessThanConstraint,
    MaximizeObjective,
    MinimizeObjective,
)

from pydantic import ValidationError

from badger.gui.components.data_panel import BadgerDataPanel
from badger.gui.components.data_table import (
    get_table_content_as_dict,
    set_init_data_table,
    update_init_data_table,
)
from badger.gui.mini.components.env_cbox import BadgerEnvBox
from badger.gui.windows.docs_window import BadgerDocsWindow
from badger.gui.windows.lim_vrange_dialog import BadgerLimitVariableRangeDialog
from badger.gui.windows.ind_lim_vrange_dialog import (
    BadgerIndividualLimitVariableRangeDialog,
)
from badger.gui.windows.review_dialog import BadgerReviewDialog
from badger.gui.windows.add_random_dialog import BadgerAddRandomDialog
from badger.gui.windows.message_dialog import BadgerScrollableMessageBox
from badger.gui.utils import filter_generator_config
from badger.environment import instantiate_env
from badger.errors import (
    BadgerEnvNotFoundError,
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
    BlockSignalsContext,
    load_config,
    get_badger_version,
    get_xopt_version,
    ts_float_to_str,
    _round_bounds_inward,
)


import logging

logger = logging.getLogger(__name__)


LABEL_WIDTH = 96


def format_validation_error(e: ValidationError) -> str:
    """Convert Pydantic ValidationError into a friendly message."""
    messages = ["\n"]
    for err in e.errors():
        loc = " -> ".join(str(item) for item in err["loc"])
        msg = f"{loc}: {err['msg']}\n"
        messages.append(msg)
    return "\n".join(messages)


def extract_constraint_symbol_and_value(constraint):
    if isinstance(constraint, GreaterThanConstraint):
        return ">", constraint.value
    if isinstance(constraint, LessThanConstraint):
        return "<", constraint.value
    else:  # Expand for other constraints if needed
        return "", 0


def extract_objective_symbol(objective: BaseObjective) -> str:
    """
    Extract text from gest-api objective objects
    """
    if isinstance(objective, MinimizeObjective):
        return "MINIMIZE"
    if isinstance(objective, MaximizeObjective):
        return "MAXIMIZE"
    else:
        raise ValueError(f"Unknown objective type: {objective}")


class BadgerRoutinePage(QWidget):
    sig_updated = pyqtSignal(str, str)  # routine name, routine description
    sig_load_template = pyqtSignal(str)  # template path
    sig_save_template = pyqtSignal(str)  # template path
    sig_go_run = pyqtSignal()
    sig_select_env = pyqtSignal(str)

    def __init__(self):
        logger.info("Initializing BadgerRoutinePage.")
        super().__init__()

        self.generators = list_generators()
        self.envs = list_env()
        self.env = None
        self.routine = None
        self.script = ""
        self.window_docs = BadgerDocsWindow(self, "")
        self.window_env_docs = BadgerDocsWindow(self, "", plugin_type="environment")
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
        # self.env_box.relative_to_curr.setChecked(True)
        # remember user selection from lim_vrange_dialog gui
        # 2: not initialized, 1: apply to all, 0: apply to only visible
        self.lim_apply_to_vars = 2

    def init_ui(self):
        logger.info("Initializing UI for BadgerRoutinePage.")
        self.config_singleton = config_singleton = init_settings()

        # Set up the layout
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(8, 12, 8, 0)

        self.tabs = tabs = QTabWidget()
        vbox.addWidget(tabs)

        tabs.tabBar().setExpanding(False)  # keep tabs at content width
        tabs.setStyleSheet("QTabWidget::tab-bar { alignment: center; }")

        self.history_browser = HistoryNavigator()
        tabs.addTab(self.history_browser, "History")

        self.edit_save = QLineEdit()
        self.edit_save.setPlaceholderText(generate_slug(2))

        self.edit_descr = QPlainTextEdit()

        # Env box
        self.BADGER_PLUGIN_ROOT = config_singleton.read_value("BADGER_PLUGIN_ROOT")

        self.env_box = BadgerEnvBox(None, self.envs, self.generators)
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
        # add extra right margin for macOS to prevent scrollbar overlap
        scroll_layout_env.setContentsMargins(0, 0, 5, 0)
        self.env_box.var_table.setColumnWidth(5, 44)

        scroll_layout_env.addWidget(self.env_box)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(scroll_content_env)
        tabs.addTab(scroll_area, "Environment + VOCS")

        # Data panel
        self.data_panel = BadgerDataPanel(self)
        # tabs.addTab(self.data_panel, "Data")

        tabs.setCurrentIndex(1)  # Show the env box by default

        # vbox.addStretch()

        # Add connection to update vocs when env or generator changes for pydantic editor validation
        # self.env_box.vocs_updated.connect(self.generator_box.update_vocs)
        self.env_box.vocs_updated.connect(self.data_panel.update_vocs)

        # Template path
        try:
            self.template_dir = config_singleton.read_value("BADGER_TEMPLATE_ROOT")
        except KeyError:
            self.template_dir = os.path.join(self.BADGER_PLUGIN_ROOT, "templates")

    def config_logic(self):
        logger.info("Configuring logic for BadgerRoutinePage.")
        # self.btn_descr_update.clicked.connect(self.update_description)
        self.env_box.load_template_button.clicked.connect(self.load_template_yaml)
        self.env_box.template_cb.currentTextChanged.connect(
            lambda: (
                self.load_template_yaml(
                    template_path=self.env_box.template_cb.currentText() + ".yaml"
                )
                if self.env_box.template_cb.currentIndex() != -1
                else None
            )
        )
        # reset template selection on history change
        # self.history_browser.history_tree_widget.itemSelectionChanged.connect(
        #    lambda: self.env_box.template_cb.setCurrentIndex(-1)
        # )
        # self.save_template_button.clicked.connect(self.save_template_yaml)
        self.env_box.algo_cb.currentIndexChanged.connect(self.select_generator)
        self.env_box.algo_cb.currentIndexChanged.connect(
            lambda: self.env_box.edit_algo_params.setMinimumHeight(
                self.env_box._qtree_height_hint(self.env_box.edit_algo_params)
            )
        )
        self.env_box.env_cb.currentIndexChanged.connect(self.select_env)
        self.env_box.var_table.sig_change_bounds.connect(
            self.adjust_variable_range_options
        )
        self.env_box.btn_env_docs.clicked.connect(self.open_environment_docs)
        self.env_box.btn_algo_docs.clicked.connect(self.open_generator_docs)
        # self.env_box.btn_lim_vrange.clicked.connect(self.limit_variable_ranges)
        self.env_box.btn_add_curr.clicked.connect(
            partial(self.fill_curr_in_init_table, record=True)
        )
        self.env_box.btn_add_rand.clicked.connect(self.show_add_rand_dialog)
        self.env_box.btn_clear.clicked.connect(
            partial(self.clear_init_table, reset_actions=True)
        )
        self.env_box.btn_add_row.clicked.connect(self.add_row_to_init_table)
        self.env_box.var_table.sig_sel_changed.connect(self.update_init_table)
        self.env_box.var_table.sig_pv_added.connect(self.handle_pv_added)
        self.env_box.var_table.sig_var_config.connect(self.handle_var_config)
        self.env_box.var_table.set_scan_range_options()

    def set_saved_values_from_init_vars(
        self, variable_names: list[str], init_vars: list[float]
    ) -> None:
        """Keep Saved column values aligned with run monitor reset targets."""
        if not variable_names or not init_vars:
            return

        values_by_name = {
            name: float(value) for name, value in zip(variable_names, init_vars)
        }
        self.env_box.var_table.set_saved_values(values_by_name)

    def load_template_yaml(
        self, checked_state=None, template_path: str | None = None
    ) -> None:
        logger.info("Loading template YAML.")
        """
        Load data from template .yaml into template_dict dictionary.
        This function expects to be called via an action from
        a QPushButton. However, if `template_path` is provided, it will
        try to directly open the file.
        """
        if (template_path is None) and isinstance(self.sender(), QPushButton):
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

        if os.path.basename(template_path) == template_path:
            template_path = os.path.join(self.template_dir, template_path)

        # Load template file
        try:
            with open(template_path, "r") as stream:
                template_dict = yaml.safe_load(stream)
                self.set_options_from_template(template_dict=template_dict)
                self.sig_load_template.emit(
                    f"Options loaded from template: {os.path.basename(template_path)}"
                )

                template_name = os.path.basename(template_path)
                self.env_box.update_template_cb(template_name)
        except (FileNotFoundError, yaml.YAMLError) as e:
            print(f"Error loading template: {e}")
            return

    def set_options_from_template(self, template_dict: dict[str, Any]):
        logger.info(
            f"Setting options from template: {template_dict.get('name', 'unknown')}"
        )
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
            env_params: dict[str, Any] = template_dict["environment"]["params"]
        except KeyError as e:
            QMessageBox.warning(self, "Error", f"Missing key in template: {e}")
            return

        # set vocs
        vocs = VOCS(
            variables={
                name: _round_bounds_inward(bounds)
                for name, bounds in template_dict["vocs"]["variables"].items()
            },
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
            self.env_box.algo_cb.setCurrentIndex(i)

            filtered_config = filter_generator_config(
                generator_name, template_dict["generator"]
            )
            self.env_box.edit_algo_params.set_params_from_generator(
                generator_name, filtered_config, vocs
            )

        # set environment
        if env_name in self.envs:
            i = self.envs.index(env_name)
            # if this changes the selected env, the ui update will trigger routine_page.select_env
            # to load the new environment
            self.env_box.set_selected_env_name(env_name)
            self.env_box.edit_env_params.set_params_from_dict(env_params)

        else:
            raise BadgerEnvNotFoundError(
                f"Template environment {env_name} not found in Badger environments"
            )

        # Load the vrange options and hard limits
        self.ratio_var_ranges = vrange_limit_options
        self.init_table_actions = initial_point_actions
        self.var_hard_limit = {
            name: _round_bounds_inward(bounds)
            for name, bounds in vrange_hard_limit.items()
        }

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

                bounds = _round_bounds_inward(bounds)

                all_variables.update({vname: bounds})
        # Override the hard limits with the ones from the routine
        all_variables.update(
            {
                name: _round_bounds_inward(bounds)
                for name, bounds in self.var_hard_limit.items()
            }
        )

        # Format for update_variables method
        all_variables = dict(sorted(all_variables.items()))
        all_variables = [{key: value} for key, value in all_variables.items()]
        self.env_box.var_table.update_variables(all_variables)

        self.env_box.var_table.set_selected(vocs.variables)
        self.env_box.var_table.addtl_vars = additional_variables

        # self.env_box.relative_to_curr.isChecked().setChecked(flag_relative)
        self.toggle_relative_to_curr(relative_to_current, refresh=False)

        if env_name:
            if relative_to_current:
                bounds, clipped = self.calc_auto_bounds()
                self.env_box.var_table.set_bounds(bounds, signal=False, clipped=clipped)
            else:
                self.env_box.var_table.set_bounds(
                    {
                        name: _round_bounds_inward(bounds)
                        for name, bounds in vocs.variables.items()
                    },
                    signal=False,
                )
            # Populate the initial table anyways, auto mode or not
            self.clear_init_table(reset_actions=False)
            self.update_init_table(force=True)

        # set objectives
        try:
            formulas = template_dict["formulas"]
        except KeyError:
            formulas = {}

        # Initialize the objective table with env observables
        try:
            formulas = template_dict["formulas"]
        except KeyError:
            formulas = {}
        objectives = []
        status = {}
        objectives_names_full = list(self.configs["observations"]) + list(
            formulas.keys()
        )
        for name in objectives_names_full:
            obj = {name: ["MINIMIZE"]}
            status[name] = False  # selected
            objectives.append(obj)
        for name, val in vocs.objectives.items():
            rule = extract_objective_symbol(val)

            idx = objectives_names_full.index(name)
            if idx == -1:
                raise BadgerRoutineError(
                    f"Objective {name} not found in the routine's observables."
                )
            else:
                objectives[idx] = {name: [rule]}
            status[name] = True

        # Show selected constraints only
        self.env_box.check_only_obj.blockSignals(True)
        self.env_box.check_only_obj.setChecked(True)
        self.env_box.check_only_obj.blockSignals(False)
        self.env_box.obj_table.show_selected_only = True

        self.env_box.obj_table.update_items(objectives, status, formulas)

        # set constraints
        # Initialize the constraints table with env observables
        try:
            formulas = template_dict["constraint_formulas"]
        except KeyError:
            formulas = {}
        constraints = []
        status = {}
        constraints_names_full = list(self.configs["observations"]) + list(
            formulas.keys()
        )
        for name in constraints_names_full:
            cons = {name: ["<", 0.0, False]}
            status[name] = False  # selected
            constraints.append(cons)
        for name, val in vocs.constraints.items():
            relation, thres = extract_constraint_symbol_and_value(val)
            critical = name in critical_constraint_names

            idx = constraints_names_full.index(name)
            if idx == -1:
                raise BadgerRoutineError(
                    f"Constraint {name} not found in the routine's observables."
                )
            else:
                constraints[idx] = {name: [relation, thres, critical]}
            status[name] = True

        # Show selected constraints only
        if any(status.values()):
            self.env_box.check_only_con.blockSignals(True)
            self.env_box.check_only_con.setChecked(True)
            self.env_box.check_only_con.blockSignals(False)
            self.env_box.con_table.show_selected_only = True

        self.env_box.con_table.update_items(constraints, status, formulas)

        # set observables
        if self.vars_env:
            # var_names = [next(iter(var)) for var in self.vars_env]
            var_names = []  # do not show var names in observables until we have a fix to get_observables
        else:
            var_names = []
        try:
            formulas = template_dict["observable_formulas"]
        except KeyError:
            formulas = {}
        observables = []
        status = {}
        observables_names_full = (
            var_names + list(self.configs["observations"]) + list(formulas.keys())
        )
        for name in observables_names_full:
            obs = {name: []}
            status[name] = False  # selected
            observables.append(obs)
        for name in vocs.observables:
            idx = observables_names_full.index(name)
            if idx == -1:
                raise BadgerRoutineError(
                    f"Observable {name} not found in the routine's observables."
                )
            else:
                observables[idx] = {name: []}
            status[name] = True

        self.env_box.sta_table.update_items(observables, status, formulas)

    def generate_template_dict_from_gui(self):
        logger.info("Generating template dictionary from GUI state.")
        """
        Generate a template dictionary from the current state of the GUI
        """

        vocs, critical_constraints = self.env_box.compose_vocs()

        # Filter generator
        generator_name = self.env_box.algo_cb.currentText()

        generator_config = self._filter_generator_params(
            generator_name=generator_name,
            generator_config=load_config(
                self.env_box.edit_algo_params.get_parameters_yaml()
            ),
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
                "name": self.env_box.env_name,
                "params": load_config(
                    self.env_box.edit_env_params.get_parameters_yaml()
                ),
            },
            "vrange_limit_options": self.ratio_var_ranges,
            "vrange_hard_limit": self.var_hard_limit,
            "additional_variables": self.env_box.var_table.addtl_vars,
            "formulas": self.env_box.obj_table.formulas,
            "constraint_formulas": self.env_box.con_table.formulas,
            "observable_formulas": self.env_box.sta_table.formulas,
            "initial_point_actions": self.init_table_actions,
            "critical_constraint_names": critical_constraints,
            "vocs": vocs.model_dump(mode="json"),
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
        logger.info("Saving routine as template YAML.")
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
            logger.error(f"Error saving template: {e}")
            return

    def refresh_ui(self, routine: Routine | None = None, silent: bool = False):
        logger.info(
            f"Refreshing UI for routine: {getattr(routine, 'name', None)} (silent={silent})"
        )
        self.generators = list_generators()
        self.envs = list_env()

        if routine is None:
            # Reset the generator and env configs
            self.env_box.algo_cb.setCurrentIndex(-1)
            self.env_box.clear_selected_env()
            init_table = self.env_box.init_table
            init_table.clear()
            hh = init_table.horizontalHeader()
            if hh:
                hh.setVisible(False)
            init_table.setRowCount(10)
            init_table.setColumnCount(0)

            # Reset the routine configs check box status
            self.env_box.check_only_var.setChecked(False)
            self.env_box.check_only_obj.setChecked(False)
            # self.env_box.relative_to_curr.setChecked(True)
            self.try_populate_init_table()

            # Reset the save settings
            name = generate_slug(2)
            self.edit_save.setText("")
            self.edit_save.setPlaceholderText(name)
            self.edit_descr.setPlainText("")

            return

        self.routine = routine  # save routine for future reference

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
        with BlockSignalsContext(self.env_box.algo_cb):
            self.env_box.algo_cb.setCurrentIndex(idx_generator)
        filtered_config = filter_generator_config(
            name_generator, routine.generator.model_dump()
        )

        vocs = routine.vocs
        # if not vocs:
        #     # Get vocs
        #     try:
        #         vocs, _ = self.env_box.compose_vocs()
        #     except Exception:
        #         vocs = None

        self.env_box.edit_algo_params.set_params_from_generator(
            name_generator, filtered_config, vocs, validate=False
        )
        self.script = routine.script

        name_env = routine.environment.name
        self.env_box.set_selected_env_name(name_env)
        env_params = routine.environment.model_dump()
        del env_params["interface"]
        self.env_box.edit_env_params.set_params_from_dict(env_params)

        # Config the vocs panel
        variables = routine.vocs.variable_names
        self.env_box.check_only_var.setChecked(True)

        self.env_box.edit_var.clear()

        try:
            self.var_hard_limit = {
                name: _round_bounds_inward(bounds)
                for name, bounds in routine.vrange_hard_limit.items()
            }
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

                bounds = _round_bounds_inward(bounds)

                all_variables.update({vname: bounds})
        # Override the hard limits with the ones from the routine
        all_variables.update(
            {
                name: _round_bounds_inward(bounds)
                for name, bounds in self.var_hard_limit.items()
            }
        )
        # Format for update_variables method
        all_variables = dict(sorted(all_variables.items()))
        all_variables = [{key: value} for key, value in all_variables.items()]

        with BlockSignalsContext(self.env_box.var_table):
            self.env_box.var_table.update_variables(variables=all_variables, filtered=2)
        self.env_box.var_table.set_selected(variables)
        self.env_box.var_table.addtl_vars = routine.additional_variables

        flag_relative = routine.relative_to_current
        if flag_relative:  # load the relative to current settings
            self.ratio_var_ranges = routine.vrange_limit_options
            self.init_table_actions = routine.initial_point_actions

        self.env_box.var_table.set_scan_range_options()

        # self.env_box.relative_to_curr.setChecked(flag_relative)

        self.toggle_relative_to_curr(flag_relative, refresh=False)

        # Always use ranges stored in routine
        self.env_box.var_table.set_bounds(
            {
                name: _round_bounds_inward(bounds)
                for name, bounds in routine.vocs.variables.items()
            },
            signal=False,
        )

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

        objectives = []
        status = {}
        objectives_names_full = list(self.configs["observations"]) + list(
            formulas.keys()
        )
        for name in objectives_names_full:
            obj = {name: ["MINIMIZE"]}
            status[name] = False  # selected
            objectives.append(obj)
        for name, val in routine.vocs.objectives.items():
            rule = extract_objective_symbol(val)

            idx = objectives_names_full.index(name)
            if idx == -1:
                raise BadgerRoutineError(
                    f"Objective {name} not found in the routine's observables."
                )
            else:
                objectives[idx] = {name: [rule]}
            status[name] = True

        # Show selected objectives only
        self.env_box.check_only_obj.blockSignals(True)
        self.env_box.check_only_obj.setChecked(True)
        self.env_box.check_only_obj.blockSignals(False)
        self.env_box.edit_obj.blockSignals(True)
        self.env_box.edit_obj.setText("")
        self.env_box.edit_obj.blockSignals(False)
        self.env_box.obj_table.keyword = ""
        self.env_box.obj_table.show_selected_only = True
        with BlockSignalsContext(self.env_box.obj_table):
            self.env_box.obj_table.update_items(objectives, status, formulas)

        # Initialize the constraints table with env observables
        try:
            formulas = routine.constraint_formulas
        except AttributeError:
            formulas = {}
        constraints = []
        status = {}
        constraints_names_full = list(self.configs["observations"]) + list(
            formulas.keys()
        )
        for name in constraints_names_full:
            cons = {name: ["<", 0.0, False]}
            status[name] = False  # selected
            constraints.append(cons)
        for name, val in routine.vocs.constraints.items():
            relation, thres = extract_constraint_symbol_and_value(val)
            critical = name in routine.critical_constraint_names

            idx = constraints_names_full.index(name)
            if idx == -1:
                raise BadgerRoutineError(
                    f"Constraint {name} not found in the routine's observables."
                )
            else:
                constraints[idx] = {name: [relation, thres, critical]}
            status[name] = True

        # Show selected constraints only
        if any(status.values()):
            self.env_box.check_only_con.blockSignals(True)
            self.env_box.check_only_con.setChecked(True)
            self.env_box.check_only_con.blockSignals(False)
        self.env_box.edit_con.blockSignals(True)
        self.env_box.edit_con.setText("")
        self.env_box.edit_con.blockSignals(False)
        self.env_box.con_table.keyword = ""
        # self.env_box.con_table.show_selected_only = False

        self.env_box.con_table.update_items(constraints, status, formulas)

        # Initialize the observables table with env observables
        if self.vars_env:
            # var_names = [next(iter(var)) for var in self.vars_env]
            var_names = []  # do not show var names in observables until we have a fix to get_observables
        else:
            var_names = []
        try:
            formulas = routine.observable_formulas
        except AttributeError:
            formulas = {}
        observables = []
        status = {}
        observables_names_full = (
            var_names + list(self.configs["observations"]) + list(formulas.keys())
        )
        for name in observables_names_full:
            obs = {name: []}
            status[name] = False  # selected
            observables.append(obs)
        for name in routine.vocs.observables:
            idx = observables_names_full.index(name)
            if idx == -1:
                raise BadgerRoutineError(
                    f"Observable {name} not found in the routine's observables."
                )
            else:
                observables[idx] = {name: []}
            status[name] = True

        # Config the metadata
        self.edit_save.setPlaceholderText(generate_slug(2))
        self.edit_save.setText(routine.name)
        self.edit_descr.setPlainText(routine.description)

        # self.generator_box.check_use_script.setChecked(not not self.script)

    def set_routine(self, routine: Routine, silent: bool = False):
        self.refresh_ui(routine, silent=silent)

    def select_generator(self, i: int):
        logger.info(
            f"Generator selected: {self.env_box.algo_cb.itemText(i)} (index={i})"
        )
        # Reset the script
        self.script = ""
        # self.generator_box.check_use_script.setChecked(False)

        if i == -1:
            self.env_box.edit_algo_params.clear()
            # self.generator_box.cb_scaling.setCurrentIndex(-1)
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

        # Get vocs
        try:
            vocs, _ = self.env_box.compose_vocs()
        except Exception:
            vocs = None
        self.env_box.edit_algo_params.set_params_from_generator(
            name, filtered_config, vocs
        )

        # Update the docs
        self.window_docs.update_docs(name, "generator")

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

    def script_updated(self, text):
        logger.info("Script updated.")
        self.script = text
        self.refresh_params_generator()

    def create_env(self):
        logger.info("Creating environment instance.")
        env_params = load_config(self.env_box.edit_env_params.get_parameters_yaml())
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
                vocs, _ = self.env_box.compose_vocs()
            except Exception:
                vocs = None
            # Function generate comes from the script
            params_generator = tmp["generate"](env, vocs)
            self.env_box.edit_algo_params.set_params_from_generator(
                self.routine.generator.name, params_generator, vocs
            )
        except Exception as e:
            QMessageBox.warning(self, "Invalid script!", str(e))

    def select_env(self, i: int):
        logger.info(f"Environment selected: {self.env_box.env_name} (index={i})")
        # Reset the initial table actions and ratio var ranges
        self.init_table_actions = []
        self.ratio_var_ranges = {}
        self.var_hard_limit = {}

        if hasattr(self, "archive_search"):
            self.archive_search.close()

        if i == -1:
            self.env_box.clear_selected_env()
            self.env_box.edit_env_params.clear()
            self.env_box.edit_var.clear()
            self.env_box.var_table.update_variables(None)
            self.configs = None
            self.env = None
            self.routine = None
            return

        name: str = self.envs[i]
        try:
            env, configs = get_env(name)
            self.configs = configs
            self.env = env
            self.env_box.edit_var.clear()
            self.env_box.edit_obj.clear()
        except Exception:
            self.configs = None
            self.env = None
            self.env_box.clear_selected_env()
            self.routine = None
            return QMessageBox.critical(self, "Error!", traceback.format_exc())

        self.env_box.set_selected_env_name(name)
        self.env_box.edit_env_params.set_params_from_dict(configs["params"])

        # Get and save vars to combine with additional vars added on the fly
        vars_env = self.vars_env = [
            {var_name: _round_bounds_inward(bounds)}
            for var in configs["variables"]
            for var_name, bounds in var.items()
        ]
        vars_combine = [*vars_env]

        # Needed for getting bounds and current values on the fly.
        # Set this before update_variables(), since that call refreshes current values.
        self.env_box.var_table.env_class, self.env_box.var_table.configs = (
            self.add_var()
        )

        self.env_box.check_only_var.blockSignals(True)
        self.env_box.check_only_var.setChecked(False)
        self.env_box.var_table.checked_only = False  # reset the checked only flag
        self.env_box.check_only_var.blockSignals(False)
        with BlockSignalsContext(self.env_box.var_table):
            self.env_box.var_table.update_variables(vars_combine)
        # Auto apply the limited variable ranges if the option is set
        if self.env_box.relative_to_curr.isChecked():
            self.set_vrange()
        self.env_box.var_table.set_scan_range_options()

        objectives = []
        status = {}
        for name in self.configs["observations"]:
            cons = {name: ["MINIMIZE"]}
            status[name] = False  # selected
            objectives.append(cons)
        self.env_box.check_only_obj.blockSignals(True)
        self.env_box.check_only_obj.setChecked(False)
        self.env_box.check_only_obj.blockSignals(False)
        self.env_box.obj_table.show_selected_only = False
        # with BlockSignalsContext(self.env_box.obj_table):
        self.env_box.obj_table.update_items(
            objectives, status, formulas={}, vocs_signal=False
        )

        # Initialize the constraints table with env observables
        constraints = []
        status = {}
        for name in self.configs["observations"]:
            cons = {name: ["<", 0.0, False]}
            status[name] = False  # selected
            constraints.append(cons)
        self.env_box.check_only_con.blockSignals(True)
        self.env_box.check_only_con.setChecked(False)
        self.env_box.check_only_con.blockSignals(False)
        self.env_box.con_table.show_selected_only = False
        # with BlockSignalsContext(self.env_box.con_table):
        self.env_box.con_table.update_items(
            constraints, status, formulas={}, vocs_signal=False
        )

        # Initialize the observable table with env variables and observables
        observables = []
        status = {}
        if self.vars_env:
            # var_names = [next(iter(var)) for var in self.vars_env]
            var_names = []  # do not show var names in observables until we have a fix to get_observables
        else:
            var_names = []
        for name in var_names + list(self.configs["observations"]):
            obs = {name: []}
            status[name] = False  # selected
            observables.append(obs)
        self.env_box.check_only_sta.blockSignals(True)
        self.env_box.check_only_sta.setChecked(False)
        self.env_box.check_only_sta.blockSignals(False)
        self.env_box.sta_table.show_selected_only = False
        # with BlockSignalsContext(self.env_box.sta_table):
        self.env_box.sta_table.update_items(
            observables, status, formulas={}, vocs_signal=False
        )

        # Update the docs
        self.window_env_docs.update_docs(env.name, "environment")

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
        logger.info(f"Filling current values in init table (record={record})")
        env = self.create_env()
        table = self.env_box.init_table
        vname_selected = self.get_init_table_header()

        if not vname_selected:
            return

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
                    item = QTableWidgetItem(f"{var_curr[name]:.6g}")
                    table.setItem(row, col, item)
                break  # Stop after filling the first non-empty row

        if record and self.env_box.relative_to_curr.isChecked():
            self.init_table_actions.append({"type": "add_curr"})

    def save_add_rand_config(self, add_rand_config):
        self.add_rand_config = add_rand_config

    def add_rand_in_init_table(self, add_rand_config=None, record=True):
        logger.info(
            f"Adding random points in init table (config={add_rand_config}, record={record})"
        )
        if add_rand_config is None:
            add_rand_config = self.add_rand_config

        # Get current point
        env = self.create_env()
        vname_selected = self.get_init_table_header()

        if not vname_selected:
            return

        var_curr = env.get_variables(vname_selected)

        # get small region around current point to sample
        vocs, _ = self.env_box.compose_vocs()

        n_point = add_rand_config["n_points"]
        fraction = add_rand_config["fraction"]
        random_sample_region = get_local_region(var_curr, vocs, fraction=fraction)
        with warnings.catch_warnings(record=True) as caught_warnings:
            try:
                random_points = random_inputs(
                    vocs, n_point, custom_bounds=random_sample_region
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
                        item = QTableWidgetItem(f"{point[name]:.6g}")
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
        logger.info(f"Clearing init table (reset_actions={reset_actions})")
        table = self.env_box.init_table
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item:
                    item.setText("")  # Set the cell content to an empty string

        if reset_actions and self.env_box.relative_to_curr.isChecked():
            self.init_table_actions = []  # reset the recorded actions

    def add_row_to_init_table(self):
        logger.info("Adding row to init table.")
        table = self.env_box.init_table
        row_position = table.rowCount()
        table.insertRow(row_position)

        for col in range(table.columnCount()):
            item = QTableWidgetItem("")
            table.setItem(row_position, col, item)

    def open_generator_docs(self):
        name = self.env_box.algo_cb.currentText()
        self.window_docs.update_docs(name, "generator")
        self.window_docs.show()

    def open_environment_docs(self):
        self.window_env_docs.show()

    def add_var(self):
        # TODO: Use a cached env
        env_params = load_config(self.env_box.edit_env_params.get_parameters_yaml())
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
        clipped = {}
        # 0: ratio with current value, 1: ratio with full range, 2: delta around current value
        if option_idx == 1:
            ratio = self.limit_option["ratio_full"]
            for i, name in enumerate(vname_selected):
                hard_bounds = vrange[name]
                delta = 0.5 * ratio * (hard_bounds[1] - hard_bounds[0])
                bounds = [var_curr[name] - delta, var_curr[name] + delta]
                new_bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
                clipped[name] = bounds != new_bounds
                vrange[name] = new_bounds
        elif option_idx == 2:
            delta = self.limit_option["delta"]
            for i, name in enumerate(vname_selected):
                hard_bounds = vrange[name]
                bounds = [var_curr[name] - delta, var_curr[name] + delta]
                new_bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
                clipped[name] = bounds != new_bounds
                vrange[name] = new_bounds
        else:
            ratio = self.limit_option["ratio_curr"]
            for i, name in enumerate(vname_selected):
                hard_bounds = vrange[name]
                sign = np.sign(var_curr[name])
                bounds = [
                    var_curr[name] * (1 - 0.5 * sign * ratio),
                    var_curr[name] * (1 + 0.5 * sign * ratio),
                ]
                new_bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
                clipped[name] = bounds != new_bounds
                vrange[name] = new_bounds

        with BlockSignalsContext(self.env_box.var_table):
            self.env_box.var_table.set_bounds(vrange, clipped=clipped)
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
        self.env_box.var_table.set_scan_range_options()

    def set_ind_vrange(self, vname, config):
        logger.info(
            f"Setting individual variable range for {vname} with config: {config}"
        )
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
            new_bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
        elif option_idx == 2:
            delta = option["delta"]
            bounds = [curr - delta, curr + delta]
            new_bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
        else:
            ratio = option["ratio_curr"]
            sign = np.sign(curr)
            bounds = [
                curr * (1 - 0.5 * sign * ratio),
                curr * (1 + 0.5 * sign * ratio),
            ]
            new_bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()

        # check if bounds have been clipped, then overwrite
        is_clipped = bounds != new_bounds
        bounds = new_bounds

        logger.info(
            f"Setting bounds for {vname}: {bounds} (hard bounds: {hard_bounds})"
        )
        # Set the bounds in the table
        self.env_box.var_table.refresh_variable(
            vname, bounds, hard_bounds, is_clipped=is_clipped
        )
        self.clear_init_table(reset_actions=False)  # clear table after changing ranges
        self.update_init_table()  # auto populate if option is set

        # Record the hard bounds for the variable
        self.var_hard_limit[vname] = hard_bounds
        # Record the ratio var ranges
        self.ratio_var_ranges[vname] = copy.deepcopy(option)
        self.env_box.var_table.set_scan_range_options()

    def adjust_variable_range_options(self, ratio: float, var_name: str = None):
        """
        Scale variable ranges by ratio and recalculate bounds

        Parameters
        ----------
        ratio : float
            Ratio applied to each variable's selected range option.
            Values > 1.0 will increase the range, values < 1.0 will decrease the range
        var_name: str (optional)
            If given a variable name, will update only that variable. Otherwise if None updates
            all selected variables
        """
        logger.info(f"Adjusting variable range options by ratio={ratio}")

        variable_names = []

        if var_name:
            variable_names = [var_name]
        else:
            variable_names = [
                name
                for name, is_selected in self.env_box.var_table.selected.items()
                if is_selected
            ]

        for vname in variable_names:
            # get copy of selected vrange option
            option = copy.copy(self.ratio_var_ranges.get(vname, self.limit_option))
            option_idx = option["limit_option_idx"]

            if option_idx == 1:
                key = "ratio_full"
            elif option_idx == 2:
                key = "delta"
            else:
                key = "ratio_curr"

            # update selected option with multiplication by ratio
            option[key] = option[key] * ratio
            self.ratio_var_ranges[vname] = option

        # recalculate bounds
        _bounds, _clipped = self.calc_auto_bounds()
        # only apply requested bounds updates
        bounds = {k: v for k, v in _bounds.items() if k in variable_names}
        clipped = {k: v for k, v in _clipped.items() if k in variable_names}
        with BlockSignalsContext(self.env_box.var_table):
            self.env_box.var_table.set_bounds(bounds, clipped=clipped)

        # recalculate initial points
        self.clear_init_table(reset_actions=False)
        self.update_init_table()
        self.env_box.var_table.set_scan_range_options()

    def save_limit_option(self, limit_option):
        logger.info(f"Saving limit option: {limit_option}")
        self.limit_option = limit_option
        self.env_box.var_table.set_scan_range_options()

    def add_var_to_list(self, name, lb, ub):
        logger.info(f"Adding variable to list: {name}, lb={lb}, ub={ub}")
        # Check if already in the list
        ok = False
        try:
            self.env_box.var_table.bounds[name]
        except KeyError:
            ok = True
        if not ok:
            logger.warning(f"Variable {name} already exists!")
            QMessageBox.warning(
                self, "Variable already exists!", f"Variable {name} already exists!"
            )
            return 1

        self.env_box.add_var(name, lb, ub)
        return 0

    def update_init_table(self, force=False):
        logger.info(f"Updating init table (force={force})")
        selected = self.env_box.var_table.selected
        variable_names = [v for v in selected if selected[v]]
        update_init_data_table(self.env_box.init_table, variable_names)

        if (not force) and (not self.env_box.relative_to_curr.isChecked()):
            return

        # Auto populate the initial table based on recorded actions
        if not self.init_table_actions:
            logger.info("No init_table_actions recorded, using default actions.")
            self.init_table_actions = [
                {"type": "add_curr"},
                {"type": "add_rand", "config": self.add_rand_config},
            ]
        self.clear_init_table(reset_actions=False)
        self._fill_init_table()

    def calc_auto_bounds(self):
        logger.info("Calculating auto bounds for selected variables.")
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
        clipped = {}

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
                new_bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
                clipped[name] = bounds != new_bounds
                vrange[name] = new_bounds
                logger.info(f"Auto bounds for {name} (full range): {new_bounds}")
            elif option_idx == 2:
                delta = limit_option["delta"]
                hard_bounds = vrange[name]
                bounds = [var_curr[name] - delta, var_curr[name] + delta]
                new_bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
                clipped[name] = bounds != new_bounds
                vrange[name] = new_bounds
                logger.info(f"Auto bounds for {name} (delta): {new_bounds}")
            else:
                ratio = limit_option["ratio_curr"]
                hard_bounds = vrange[name]
                sign = np.sign(var_curr[name])
                bounds = [
                    var_curr[name] * (1 - 0.5 * sign * ratio),
                    var_curr[name] * (1 + 0.5 * sign * ratio),
                ]
                new_bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
                clipped[name] = bounds != new_bounds
                vrange[name] = new_bounds
                logger.info(f"Auto bounds for {name} (current ratio): {new_bounds}")

        return vrange, clipped

    def toggle_relative_to_curr(self, checked, refresh=True):
        logger.info(f"Toggling relative_to_curr: checked={checked}, refresh={refresh}")
        if checked:
            try:
                _ = self.env_box.compose_vocs()
            except Exception:
                logger.warning("Variable range is not valid, switching to manual mode.")
                QTimer.singleShot(
                    0, lambda: self.env_box.relative_to_curr.isChecked()
                )  # ??
                QMessageBox.warning(
                    self,
                    "Variable range is not valid!",
                    "Please fix the invalid variable range before enabling auto mode.",
                )
                return

            # self.env_box.switch_var_panel_style(True)

            if refresh and self.env_box.var_table.selected:
                logger.info("Refreshing auto bounds and initial table.")
                bounds, clipped = self.calc_auto_bounds()
                self.env_box.var_table.set_bounds(bounds, clipped=clipped)
                self.clear_init_table(reset_actions=False)
                self.try_populate_init_table()

            # self.env_box.var_table.lock_bounds()
            self.env_box.init_table.set_uneditable()
        else:
            logger.info("Switching to manual variable range mode.")
            # self.env_box.switch_var_panel_style(False)

            self.env_box.var_table.unlock_bounds()
            self.env_box.init_table.set_editable()

    def refresh_variables(self):
        logger.info("Refreshing variables and bounds.")
        variables = self.env_box.var_table.export_variables()
        bounds, clipped = self.calc_auto_bounds()

        no_need_to_update = True
        for vname in variables:
            if not np.allclose(bounds[vname], variables[vname]):
                no_need_to_update = False
                break
        if no_need_to_update:
            logger.info("No need to update variable bounds.")
            return

        logger.info("Updating variable bounds and initial table.")
        self.env_box.var_table.set_bounds(bounds, clipped=clipped)
        self.clear_init_table(reset_actions=False)
        self.try_populate_init_table()

    def try_populate_init_table(self):
        logger.info("Trying to auto-populate initial table.")
        if (
            self.env_box.relative_to_curr.isChecked()
            and self.env_box.var_table.selected
        ):
            self.update_init_table()

    def handle_pv_added(self):
        logger.info("Handling PV added event.")
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
                bounds = _round_bounds_inward(bounds)
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
        self.env_box.var_table.data_changed.emit()

    def _compose_routine(self) -> Routine:
        logger.info("Composing routine from GUI state.")
        # Compose the routine
        # Metadata
        name = self.edit_save.text() or self.edit_save.placeholderText()
        description = self.edit_descr.toPlainText()

        # General sanity checks
        if self.env_box.algo_cb.currentIndex() == -1:
            logger.error("No generator selected.")
            raise BadgerRoutineError("no generator selected")
        env_name = self.env_box.get_selected_env_name()
        if not env_name:
            logger.error("No environment selected.")
            raise BadgerRoutineError("no environment selected")
        if env_name not in self.envs:
            logger.error(f"Environment not found: {env_name}")
            raise BadgerRoutineError(f"environment not found: {env_name}")

        # Generator
        generator_name = self.generators[self.env_box.algo_cb.currentIndex()]
        generator_params = load_config(
            self.env_box.edit_algo_params.get_parameters_yaml()
        )
        logger.debug(
            f"Generator selected: {generator_name}, params: {generator_params}"
        )
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
        env_params = load_config(self.env_box.edit_env_params.get_parameters_yaml())
        logger.debug(f"Environment selected: {env_name}, params: {env_params}")

        # VOCS
        vocs, critical_constraints = self.env_box.compose_vocs()
        logger.debug(
            f"VOCS composed: variables={list(vocs.variables.keys())}, objectives={list(vocs.objectives.keys())}, constraints={list(vocs.constraints.keys())}"
        )
        if not vocs.variables:
            logger.error("No variables selected.")
            raise BadgerRoutineError("no variables selected")
        if not vocs.objectives:
            logger.error("No objectives selected.")
            raise BadgerRoutineError("no objectives selected")

        # Initial points
        init_points_df = pd.DataFrame.from_dict(
            get_table_content_as_dict(self.env_box.init_table)
        )
        init_points_df = init_points_df.replace("", pd.NA)
        init_points_df = init_points_df.dropna(subset=init_points_df.columns, how="all")
        if init_points_df.empty:
            logger.error("No initial points provided.")
            raise BadgerRoutineError(
                "No initial points provided. Please add at least one initial point"
            )
        contains_na = init_points_df.isna().any().any()
        if contains_na:
            logger.error("Initial points are not valid, missing values detected.")
            raise BadgerRoutineError(
                "Initial points are not valid, please fill in the missing values"
            )

        # Script that generates generator params
        # if self.generator_box.check_use_script.isChecked():
        #    script = self.script
        #    logger.debug("Using custom script for generator params.")
        # else:
        #    script = None

        # Relative to current params
        if self.env_box.relative_to_curr.isChecked():
            relative_to_current = True
            vrange_limit_options = self.ratio_var_ranges
            initial_point_actions = self.init_table_actions
            logger.debug("Routine is set to use relative to current variable ranges.")
        else:
            relative_to_current = False
            vrange_limit_options = None
            initial_point_actions = None
            logger.debug("Routine is set to use manual variable ranges.")

        # Save hard limits no matter relative to current or not
        vrange_hard_limit = self.var_hard_limit

        try:
            generator_params.pop("vocs")  # remove vocs if present
            generator = get_generator_dynamic(generator_name)(
                vocs=vocs, **generator_params
            )
            logger.info(f"Generator instance created: {generator_name}")
        except ValidationError as e:
            logger.error(f"Algorithm validation failed: {format_validation_error(e)}")
            raise BadgerRoutineError(
                f"\n\nAlgorithm validation failed: {format_validation_error(e)}"
            ) from e

        with warnings.catch_warnings(record=True) as caught_warnings:
            routine = Routine(
                # Metadata
                badger_version=get_badger_version(),
                xopt_version=get_xopt_version(),
                creation_ts=ts_float_to_str(datetime.now().timestamp(), "lcls-fname"),
                # Xopt part
                generator=generator,
                # Badger part
                name=name,
                description=description,
                environment={"name": env_name} | env_params,
                initial_points=init_points_df.astype("double"),
                critical_constraint_names=critical_constraints,
                tags=None,
                # script=script,
                relative_to_current=relative_to_current,
                vrange_limit_options=vrange_limit_options,
                vrange_hard_limit=vrange_hard_limit,
                initial_point_actions=initial_point_actions,
                additional_variables=self.env_box.var_table.addtl_vars,
                formulas=self.env_box.obj_table.formulas,
                constraint_formulas=self.env_box.con_table.formulas,
                observable_formulas=self.env_box.sta_table.formulas,
            )

            # Check if any user warnings were caught
            for warning in caught_warnings:
                if issubclass(warning.category, UserWarning):
                    logger.warning(f"UserWarning caught: {warning.message}")
                    QMessageBox.warning(
                        self,
                        "Warning!",
                        f"Warning: {warning.message}",
                    )
                else:
                    logger.warning(f"Caught warning: {warning.message}")

            logger.info(f"Routine composed successfully: {routine.name}")
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
