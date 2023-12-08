import sqlite3
import traceback
from typing import List

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
from xopt.generators import get_generator_defaults

from .generator_cbox import BadgerAlgoBox
from .constraint_item import constraint_item
from .data_table import get_table_content_as_dict, set_init_data_table
from .env_cbox import BadgerEnvBox
from .filter_cbox import BadgerFilterBox
from .state_item import state_item
from ..windows.docs_window import BadgerDocsWindow
from ..windows.edit_script_dialog import BadgerEditScriptDialog
from ..windows.lim_vrange_dialog import BadgerLimitVariableRangeDialog
from ..windows.review_dialog import BadgerReviewDialog
from ..windows.var_dialog import BadgerVariableDialog
from ....db import save_routine, remove_routine, update_routine
from ....environment import instantiate_env
from ....errors import BadgerRoutineError
from ....factory import list_generators, list_env, get_env
from ....routine import Routine
from ....settings import read_value
from ....utils import get_yaml_string, load_config, strtobool

CONS_RELATION_DICT = {
    '>': 'GREATER_THAN',
    '<': 'LESS_THAN',
    '=': 'EQUAL_TO',
}


class BadgerRoutinePage(QWidget):
    sig_updated = pyqtSignal(str, str)  # routine name, routine description

    def __init__(self):
        super().__init__()

        self.generators = list_generators()
        self.envs = list_env()
        self.env = None
        self.routine = None
        self.script = ''
        self.window_docs = BadgerDocsWindow(self, '')

        # Limit variable ranges
        self.limit_option = None

        self.init_ui()
        self.config_logic()

    def init_ui(self):
        # Set up the layout
        vbox = QVBoxLayout(self)
        vbox.setContentsMargins(11, 11, 19, 11)

        # Meta group
        group_meta = QGroupBox('Metadata')
        group_meta.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        vbox_meta = QVBoxLayout(group_meta)

        # Name
        name = QWidget()
        hbox_name = QHBoxLayout(name)
        hbox_name.setContentsMargins(0, 0, 0, 0)
        label = QLabel('Name')
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
        lbl_descr = QLabel('Descr')
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
        self.cbox_tags = cbox_tags = BadgerFilterBox(title=' Tags')
        if not strtobool(read_value('BADGER_ENABLE_ADVANCED')):
            cbox_tags.hide()
        vbox_meta.addWidget(cbox_tags, alignment=Qt.AlignTop)
        # vbox_meta.addStretch()

        vbox.addWidget(group_meta)

        # Algo box
        self.generator_box = BadgerAlgoBox(None, self.generators)
        self.generator_box.expand()  # expand the box initially
        vbox.addWidget(self.generator_box)

        # Env box
        self.env_box = BadgerEnvBox(None, self.envs)
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
        self.env_box.btn_add_var.clicked.connect(self.add_var)
        self.env_box.btn_lim_vrange.clicked.connect(self.limit_variable_ranges)
        self.env_box.btn_add_con.clicked.connect(self.add_constraint)
        self.env_box.btn_add_sta.clicked.connect(self.add_state)
        self.env_box.btn_add_curr.clicked.connect(self.fill_curr_in_init_table)
        self.env_box.btn_clear.clicked.connect(self.clear_init_table)
        self.env_box.btn_add_row.clicked.connect(self.add_row_to_init_table)

    def refresh_ui(self, routine: Routine = None):
        self.routine = routine  # save routine for future reference

        self.generators = list_generators()
        self.envs = list_env()
        # Clean up the constraints/states list
        self.env_box.list_con.clear()
        self.env_box.list_sta.clear()

        if routine is None:
            # Reset the generator and env configs
            self.generator_box.cb.setCurrentIndex(-1)
            self.env_box.cb.setCurrentIndex(-1)

            # Reset the routine configs check box status
            self.env_box.check_only_var.setChecked(False)
            self.env_box.check_only_obj.setChecked(False)

            # Reset the save settings
            name = generate_slug(2)
            self.edit_save.setText('')
            self.edit_save.setPlaceholderText(name)
            self.edit_descr.setPlainText('')
            self.btn_descr_update.setDisabled(True)

            return

        # Enable description edition
        self.btn_descr_update.setDisabled(False)
        # Fill in the generator and env configs
        name_generator = routine.generator.name
        idx_generator = self.generators.index(name_generator)
        self.generator_box.cb.setCurrentIndex(idx_generator)
        # self.generator_box.edit.setPlainText(routine.generator.yaml())
        self.generator_box.edit.setPlainText(
            get_yaml_string(routine.generator.model_dump()))
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
        self.env_box.var_table.set_selected(variables)
        self.env_box.var_table.set_bounds(routine.vocs.variables)

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
                relation = ['GREATER_THAN', 'LESS_THAN',
                            'EQUAL_TO'].index(relation)
                self.add_constraint(name, relation, thres, critical)

        constants = routine.vocs.constants
        if len(constants):
            for name_sta, val in constants.items():
                self.add_state(name_sta)

        # Config the metadata
        self.edit_save.setPlaceholderText(generate_slug(2))
        self.edit_save.setText(routine.name)
        self.edit_descr.setPlainText(routine.description)

        self.generator_box.check_use_script.setChecked(not not self.script)

    def select_generator(self, i):
        # Reset the script
        self.script = ''
        self.generator_box.check_use_script.setChecked(False)

        if i == -1:
            self.generator_box.edit.setPlainText('')
            self.generator_box.cb_scaling.setCurrentIndex(-1)
            return

        name = self.generators[i]
        default_config = get_generator_defaults(name)
        self.generator_box.edit.setPlainText(get_yaml_string(default_config))

        # Update the docs
        self.window_docs.update_docs(name)

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
            intf_name = self.configs['interface'][0]
        except KeyError:
            intf_name = None
        configs = {
            'params': env_params,
            'interface': [intf_name]
        }
        env = instantiate_env(self.env, configs)

        return env

    def refresh_params_generator(self):
        if not self.script:
            return

        try:
            tmp = {}
            exec(self.script, tmp)
            try:
                tmp['generate']  # test if generate function is defined
            except Exception as e:
                QMessageBox.warning(self, 'Please define a valid generate function!', str(e))
                return

            env = self.create_env()
            # Get vocs
            try:
                vocs = self._compose_vocs()
            except Exception:
                vocs = None
            # Function generate comes from the script
            params_generator = tmp['generate'](env, vocs)
            self.generator_box.edit.setPlainText(get_yaml_string(params_generator))
        except Exception as e:
            QMessageBox.warning(self, 'Invalid script!', str(e))

    def select_env(self, i):
        if i == -1:
            self.env_box.edit.setPlainText('')
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
        except:
            self.configs = None
            self.env = None
            self.env_box.cb.setCurrentIndex(-1)
            self.env_box.btn_add_con.setDisabled(True)
            self.env_box.btn_add_sta.setDisabled(True)
            self.env_box.btn_add_var.setDisabled(True)
            self.env_box.btn_lim_vrange.setDisabled(True)
            self.routine = None
            return QMessageBox.critical(
                self,
                'Error!',
                traceback.format_exc()
            )

        self.env_box.edit.setPlainText(get_yaml_string(configs['params']))

        vars_env = configs['variables']
        vars_combine = [*vars_env]

        self.env_box.check_only_var.setChecked(False)
        self.env_box.var_table.update_variables(vars_combine)

        _objs_env = configs['observations']
        objs_env = []
        for name in _objs_env:
            obj = {}
            obj[name] = 'MINIMIZE'  # default rule
            objs_env.append(obj)
        self.env_box.check_only_obj.setChecked(False)
        self.env_box.obj_table.update_objectives(objs_env)

        self.env_box.list_con.clear()
        self.env_box.list_sta.clear()
        self.env_box.fit_content()
        # self.routine = None

    def get_init_table_header(self):
        table = self.env_box.init_table
        header_list = []
        for col in range(table.columnCount()):
            item = table.horizontalHeaderItem(col)
            if item:
                header_list.append(item.text())
            else:
                header_list.append('')  # Handle the case where the header item is None
        return header_list

    def fill_curr_in_init_table(self):
        env = self.create_env()
        table = self.env_box.init_table
        vname_selected = self.get_init_table_header()
        var_curr = env._get_variables(vname_selected)

        # Iterate through the rows
        for row in range(table.rowCount()):
            # Check if the row is empty
            if np.all([not table.item(row, col).text() for col in range(table.columnCount())]):
                # Fill the row with content_list
                for col, name in enumerate(vname_selected):
                    item = QTableWidgetItem(str(var_curr[name]))
                    table.setItem(row, col, item)
                break  # Stop after filling the first non-empty row

    def clear_init_table(self):
        table = self.env_box.init_table
        for row in range(table.rowCount()):
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item:
                    item.setText('')  # Set the cell content to an empty string

    def add_row_to_init_table(self):
        table = self.env_box.init_table
        row_position = table.rowCount()
        table.insertRow(row_position)

        for col in range(table.columnCount()):
            item = QTableWidgetItem('')
            table.setItem(row_position, col, item)

    def open_playground(self):
        pass

    def open_generator_docs(self):
        self.window_docs.show()

    def add_var(self):
        # TODO: Use a cached env
        env_params = load_config(self.env_box.edit.toPlainText())
        try:
            intf_name = self.configs['interface'][0]
        except KeyError:
            intf_name = None
        configs = {
            'params': env_params,
            'interface': [intf_name]
        }

        dlg = BadgerVariableDialog(self, self.env, configs, self.add_var_to_list)
        dlg.exec()

    def limit_variable_ranges(self):
        dlg = BadgerLimitVariableRangeDialog(
            self, self.set_vrange,
            self.save_limit_option,
            self.limit_option,
        )
        dlg.exec()

    def set_vrange(self):
        vname_selected = []
        vrange = {}

        for var in self.env_box.var_table.all_variables:
            name = next(iter(var))
            if self.env_box.var_table.is_checked(name):
                vname_selected.append(name)
                vrange[name] = var[name]

        env = self.create_env()
        var_curr = env._get_variables(vname_selected)

        option_idx = self.limit_option['limit_option_idx']
        if option_idx:
            ratio = self.limit_option['ratio_full']
            for i, name in enumerate(vname_selected):
                hard_bounds = vrange[name]
                delta = 0.5 * ratio * (hard_bounds[1] - hard_bounds[0])
                bounds = [var_curr[name] - delta, var_curr[name] + delta]
                bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
                vrange[name] = bounds
        else:
            ratio = self.limit_option['ratio_curr']
            for i, name in enumerate(vname_selected):
                hard_bounds = vrange[name]
                sign = np.sign(var_curr[name])
                bounds = [var_curr[name] * (1 - 0.5 * sign * ratio),
                          var_curr[name] * (1 + 0.5 * sign * ratio)]
                bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
                vrange[name] = bounds

        self.env_box.var_table.set_bounds(vrange)

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
            QMessageBox.warning(self, 'Variable already exists!', f'Variable {name} already exists!')
            return 1

        self.env_box.add_var(name, lb, ub)
        return 0

    def add_constraint(self, name=None, relation=0, threshold=0, critical=False):
        if self.configs is None:
            return

        options = self.configs['observations']
        item = QListWidgetItem(self.env_box.list_con)
        con_item = constraint_item(options,
                                   lambda: self.env_box.list_con.takeItem(
                                       self.env_box.list_con.row(item)),
                                   name, relation, threshold, critical)
        item.setSizeHint(con_item.sizeHint())
        self.env_box.list_con.addItem(item)
        self.env_box.list_con.setItemWidget(item, con_item)
        # self.env_box.dict_con[''] = item
        self.env_box.fit_content()

    def add_state(self, name=None):
        if self.configs is None:
            return

        var_names = [next(iter(d)) for d in self.configs['variables']]
        options = self.configs['observations'] + var_names
        item = QListWidgetItem(self.env_box.list_sta)
        sta_item = state_item(options,
                              lambda: self.env_box.list_sta.takeItem(
                                  self.env_box.list_sta.row(item)), name)
        item.setSizeHint(sta_item.sizeHint())
        self.env_box.list_sta.addItem(item)
        self.env_box.list_sta.setItemWidget(item, sta_item)
        self.env_box.fit_content()

    def _compose_vocs(self) -> (VOCS, List[str]):
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

        states = {}
        for i in range(self.env_box.list_sta.count()):
            raise NotImplementedError("constants/states has not been implemented yet!")
            #item = self.env_box.list_sta.item(i)
            #item_widget = self.env_box.list_sta.itemWidget(item)
            #sta_name = item_widget.cb_sta.currentText()
            #states[sta_name] =

        vocs = VOCS(
            variables=variables,
            objectives=objectives,
            constraints={},
            constants={}
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
        env_params = load_config(self.env_box.edit.toPlainText())

        # VOCS
        vocs, critical_constraints = self._compose_vocs()

        # Initial points
        init_points_df = pd.DataFrame.from_dict(
            get_table_content_as_dict(self.env_box.init_table))
        init_points_df = init_points_df.replace('', pd.NA)
        init_points_df = init_points_df.dropna(subset=init_points_df.columns,
                                               how='all')
        contains_na = init_points_df.isna().any().any()
        if contains_na:
            raise BadgerRoutineError(
                'Initial points are not valid, please fill in the missing values'
            )

        # Script that generates generator params
        if self.generator_box.check_use_script.isChecked():
            script = self.script
        else:
            script = None

        return Routine(
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
        )

    def review(self):
        try:
            routine = self._compose_routine()
        except:
            return QMessageBox.critical(
                self,
                'Invalid routine!',
                traceback.format_exc()
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
                'Update succeeded!',
                f'Routine {self.routine.name} description was updated successfully!'
            )
        except Exception:
            return QMessageBox.critical(
                self,
                'Update failed!',
                traceback.format_exc()
            )

    def save(self):
        try:
            routine = self._compose_routine()
        except ValidationError:
            return QMessageBox.critical(
                self,
                'Error!',
                traceback.format_exc()
            )

        try:
            save_routine(routine)
        except sqlite3.IntegrityError:
            return QMessageBox.critical(
                self, 'Error!',
                f'Routine {routine.name} already existed in the database! Please '
                f'choose another name.')

        return 0

    def delete(self):
        name = self.edit_save.text() or self.edit_save.placeholderText()
        remove_routine(name)

        return 0
