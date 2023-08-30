from PyQt5.QtWidgets import QLineEdit, QListWidgetItem, QWidget, QVBoxLayout, QHBoxLayout
from PyQt5.QtWidgets import QGroupBox, QLineEdit, QLabel, QMessageBox, QSizePolicy
from PyQt5.QtCore import Qt
import sqlite3
import pandas as pd
from coolname import generate_slug
from ....factory import list_algo, list_env, get_algo, get_env
from ....utils import ystring, load_config, config_list_to_dict
# from ....core import instantiate_env, list_scaling_func, get_scaling_default_params, Routine
from ....core import instantiate_env, Routine
from ....db import save_routine, remove_routine
from .constraint_item import constraint_item
from .state_item import state_item
from .algo_cbox import BadgerAlgoBox
from .env_cbox import BadgerEnvBox
from .filter_cbox import BadgerFilterBox
from ..windows.review_dialog import BadgerReviewDialog
from ..windows.var_dialog import BadgerVariableDialog
from ..windows.edit_script_dialog import BadgerEditScriptDialog
from ..windows.docs_window import BadgerDocsWindow
from .data_table import get_table_content_as_dict, set_init_data_table
from ....settings import read_value


CONS_RELATION_DICT = {
    '>': 'GREATER_THAN',
    '<': 'LESS_THAN',
    '=': 'EQUAL_TO',
}


class BadgerRoutinePage(QWidget):
    def __init__(self):
        super().__init__()

        self.algos = list_algo()
        self.envs = list_env()
        self.env = None
        self.routine = None
        self.script = ''
        # self.scaling_functions = list_scaling_func()
        self.window_docs = BadgerDocsWindow(self, '')

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

        # Tags
        self.cbox_tags = cbox_tags = BadgerFilterBox(title=' Tags')
        if not read_value('BADGER_ENABLE_ADVANCED'):
            cbox_tags.hide()
        vbox_meta.addWidget(cbox_tags, alignment=Qt.AlignTop)
        # vbox_meta.addStretch()

        vbox.addWidget(group_meta)

        # Algo box
        # self.algo_box = BadgerAlgoBox(None, self.algos, self.scaling_functions)
        self.algo_box = BadgerAlgoBox(None, self.algos)
        self.algo_box.expand()  # expand the box initially
        vbox.addWidget(self.algo_box)

        # Env box
        self.env_box = BadgerEnvBox(None, self.envs)
        self.env_box.expand()  # expand the box initially
        vbox.addWidget(self.env_box)

        vbox.addStretch()

    def config_logic(self):
        self.algo_box.cb.currentIndexChanged.connect(self.select_algo)
        self.algo_box.btn_docs.clicked.connect(self.open_algo_docs)
        self.algo_box.check_use_script.stateChanged.connect(self.toggle_use_script)
        self.algo_box.btn_edit_script.clicked.connect(self.edit_script)
        # self.algo_box.cb_scaling.currentIndexChanged.connect(self.select_scaling_func)
        self.env_box.cb.currentIndexChanged.connect(self.select_env)
        self.env_box.btn_env_play.clicked.connect(self.open_playground)
        self.env_box.btn_add_var.clicked.connect(self.add_var)
        self.env_box.btn_add_con.clicked.connect(self.add_constraint)
        self.env_box.btn_add_sta.clicked.connect(self.add_state)

    def refresh_ui(self, routine):
        self.routine = routine  # save routine for future reference

        self.algos = list_algo()
        self.envs = list_env()
        # Clean up the constraints/states list
        self.env_box.list_con.clear()
        self.env_box.list_sta.clear()

        if routine is None:
            # Reset the algo and env configs
            self.algo_box.cb.setCurrentIndex(-1)
            self.env_box.cb.setCurrentIndex(-1)

            # Reset the routine configs check box status
            self.env_box.check_only_var.setChecked(False)
            self.env_box.check_only_obj.setChecked(False)

            # Reset the save settings
            name = generate_slug(2)
            self.edit_save.setText('')
            self.edit_save.setPlaceholderText(name)

            return

        # Fill in the algo and env configs
        name_algo = routine['algo']
        idx_algo = self.algos.index(name_algo)
        self.algo_box.cb.setCurrentIndex(idx_algo)
        self.algo_box.edit.setPlainText(ystring(routine['algo_params']))
        try:
            self.script = routine['config']['script']
        except KeyError:
            self.script = None
        try:
            name_scaling = routine['config']['domain_scaling']['func']
            params_scaling = routine['config']['domain_scaling'].copy()
            del params_scaling['func']
        except:
            name_scaling = None
            params_scaling = None
        
        '''
        try:
            idx_scaling = self.scaling_functions.index(name_scaling)
        except ValueError:
            idx_scaling = -1
        self.algo_box.cb_scaling.setCurrentIndex(idx_scaling)
        '''
        
        self.algo_box.edit_scaling.setPlainText(ystring(params_scaling))

        name_env = routine['env']
        idx_env = self.envs.index(name_env)
        self.env_box.cb.setCurrentIndex(idx_env)
        self.env_box.edit.setPlainText(ystring(routine['env_params']))

        # Config the vocs panel
        variables = [next(iter(v)) for v in routine['config']['variables']]
        self.env_box.check_only_var.setChecked(True)
        self.env_box.edit_var.clear()
        self.env_box.var_table.set_selected(variables)
        self.env_box.var_table.set_bounds(routine['config']['variables'])

        try:
            init_points = routine['config']['init_points']
            set_init_data_table(self.env_box.init_table, init_points)
        except KeyError:
            set_init_data_table(self.env_box.init_table, None)

        objectives = [next(iter(v)) for v in routine['config']['objectives']]
        self.env_box.check_only_obj.setChecked(True)
        self.env_box.edit_obj.clear()
        self.env_box.obj_table.set_selected(objectives)
        self.env_box.obj_table.set_rules(routine['config']['objectives'])

        if routine['config']['constraints'] is not None:
            for i in range(len(routine['config']['constraints'])):
                name = next(iter(routine['config']['constraints'][i]))
                relation, thres = routine['config']['constraints'][i][name][:2]
                try:
                    routine['config']['constraints'][i][name][2]
                    critical = True
                except:
                    critical = False
                relation = ['GREATER_THAN', 'LESS_THAN',
                            'EQUAL_TO'].index(relation)
                self.add_constraint(name, relation, thres, critical)

        try:
            config_states = routine['config']['states']
        except KeyError:
            config_states = None
        if config_states is not None:
            for name_sta in config_states:
                self.add_state(name_sta)

        # Config the metadata
        name = routine['name']
        self.edit_save.setPlaceholderText(generate_slug(2))
        self.edit_save.setText(name)
        try:
            tags = routine['config']['tags']
        except:
            tags = {}
        try:
            self.cbox_tags.cb_obj.setCurrentText(tags['objective'])
        except:
            self.cbox_tags.cb_obj.setCurrentIndex(0)
        try:
            self.cbox_tags.cb_reg.setCurrentText(tags['region'])
        except:
            self.cbox_tags.cb_reg.setCurrentIndex(0)
        try:
            self.cbox_tags.cb_gain.setCurrentText(tags['gain'])
        except:
            self.cbox_tags.cb_gain.setCurrentIndex(0)

        self.algo_box.check_use_script.setChecked(not not self.script)

    def select_algo(self, i):
        # Reset the script
        self.script = ''
        self.algo_box.check_use_script.setChecked(False)

        if i == -1:
            self.algo_box.edit.setPlainText('')
            self.algo_box.cb_scaling.setCurrentIndex(-1)
            return

        name = self.algos[i]
        try:
            _, configs = get_algo(name)
            self.algo_box.edit.setPlainText(ystring(configs['params']))

            # Update the docs
            self.window_docs.update_docs(name)
        except Exception as e:
            self.algo_box.cb.setCurrentIndex(-1)
            return QMessageBox.critical(self, 'Error!', str(e))

    def toggle_use_script(self):
        if self.algo_box.check_use_script.isChecked():
            self.algo_box.btn_edit_script.show()
            self.algo_box.edit.setReadOnly(True)
            self.refresh_params_algo()
        else:
            self.algo_box.btn_edit_script.hide()
            self.algo_box.edit.setReadOnly(False)

    def edit_script(self):
        algo = self.algo_box.cb.currentText()
        dlg = BadgerEditScriptDialog(self, algo, self.script, self.script_updated)
        dlg.exec()

    def script_updated(self, text):
        self.script = text
        self.refresh_params_algo()

    def refresh_params_algo(self):
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
            # Get vocs
            try:
                vocs = self._compose_vocs()
            except Exception:
                vocs = None
            # Function generate comes from the script
            params_algo = tmp['generate'](env, vocs)
            self.algo_box.edit.setPlainText(ystring(params_algo))
        except Exception as e:
            QMessageBox.warning(self, 'Invalid script!', str(e))
    
    '''
    def select_scaling_func(self, i):
        if i == -1:
            self.algo_box.edit_scaling.setPlainText('')
            return

        try:
            name = self.scaling_functions[i]
            default_params = get_scaling_default_params(name)
            self.algo_box.edit_scaling.setPlainText(ystring(default_params))
        except Exception as e:
            self.algo_box.cb.setCurrentIndex(-1)
            return QMessageBox.critical(self, 'Error!', str(e))
    '''

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
            if self.algo_box.check_use_script.isChecked():
                self.refresh_params_algo()
        except Exception as e:
            self.configs = None
            self.env = None
            self.env_box.cb.setCurrentIndex(-1)
            self.env_box.btn_add_con.setDisabled(True)
            self.env_box.btn_add_sta.setDisabled(True)
            self.env_box.btn_add_var.setDisabled(True)
            self.routine = None
            return QMessageBox.critical(self, 'Error!', str(e))

        self.env_box.edit.setPlainText(ystring(configs['params']))

        vars_env = configs['variables']
        vars_combine = [*vars_env]
        if self.routine:  # check for the temp variables in vocs
            vars_vocs = self.routine['config']['variables']
            var_names_vocs = [next(iter(var)) for var in vars_vocs]
            var_names_env = [next(iter(var)) for var in vars_env]
            for name in var_names_vocs:
                if name in var_names_env:
                    continue

                _var = {}
                _var[name] = [-100, 100]  # TODO: how to get better default bounds?
                vars_combine.append(_var)
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
        self.routine = None

    def open_playground(self):
        pass

    def open_algo_docs(self):
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

    def _compose_vocs(self):
        # Compose the VOCS settings
        variables = self.env_box.var_table.export_variables()
        objectives = self.env_box.obj_table.export_objectives()

        constraints = []
        for i in range(self.env_box.list_con.count()):
            item = self.env_box.list_con.item(i)
            item_widget = self.env_box.list_con.itemWidget(item)
            critical = item_widget.check_crit.isChecked()
            con_name = item_widget.cb_obs.currentText()
            relation = CONS_RELATION_DICT[item_widget.cb_rel.currentText()]
            value = item_widget.sb.value()
            _dict = {}
            _dict[con_name] = [relation, value]
            if critical:
                _dict[con_name].append('CRITICAL')
            constraints.append(_dict)

        states = []
        for i in range(self.env_box.list_sta.count()):
            item = self.env_box.list_sta.item(i)
            item_widget = self.env_box.list_sta.itemWidget(item)
            sta_name = item_widget.cb_sta.currentText()
            states.append(sta_name)

        vocs = {
            'variables': variables,
            'objectives': objectives,
            'constraints': constraints,
            'states': states,
        }

        return vocs

    def _compose_routine(self):
        # Compose the routine
        name = self.edit_save.text() or self.edit_save.placeholderText()
        algo = self.algo_box.cb.currentText()
        assert algo, 'Please specify algorithm'
        env = self.env_box.cb.currentText()
        assert env, 'Please specify environment'
        algo_params = load_config(self.algo_box.edit.toPlainText())
        env_params = load_config(self.env_box.edit.toPlainText())

        variables = self.env_box.var_table.export_variables()
        objectives = self.env_box.obj_table.export_objectives()

        constraints = []
        for i in range(self.env_box.list_con.count()):
            item = self.env_box.list_con.item(i)
            item_widget = self.env_box.list_con.itemWidget(item)
            critical = item_widget.check_crit.isChecked()
            con_name = item_widget.cb_obs.currentText()
            relation = CONS_RELATION_DICT[item_widget.cb_rel.currentText()]
            value = item_widget.sb.value()
            _dict = {}
            _dict[con_name] = [relation, value]
            if critical:
                _dict[con_name].append('CRITICAL')
            constraints.append(_dict)

        states = []
        for i in range(self.env_box.list_sta.count()):
            item = self.env_box.list_sta.item(i)
            item_widget = self.env_box.list_sta.itemWidget(item)
            sta_name = item_widget.cb_sta.currentText()
            states.append(sta_name)

        # Domain scaling
        try:
            scaling = self.algo_box.cb_scaling.currentText()
            scaling_params = load_config(self.algo_box.edit_scaling.toPlainText())
            domain_scaling = {'func': scaling, **scaling_params}
        except:
            domain_scaling = None

        # Tags
        tag_obj = self.cbox_tags.cb_obj.currentText()
        tag_reg = self.cbox_tags.cb_reg.currentText()
        tag_gain = self.cbox_tags.cb_gain.currentText()
        tags = {}
        if tag_obj: tags['objective'] = tag_obj
        if tag_reg: tags['region'] = tag_reg
        if tag_gain: tags['gain'] = tag_gain
        if not tags: tags = None

        # Initial points
        init_points_df = pd.DataFrame.from_dict(
            get_table_content_as_dict(self.env_box.init_table))
        init_points_df = init_points_df.replace('', pd.NA)
        init_points_df = init_points_df.dropna(subset=init_points_df.columns,
                                               how='all')
        contains_na = init_points_df.isna().any().any()
        if contains_na:
            raise Exception('Initial points are not valid, please fill in the missing values')
        if init_points_df.empty:
            init_points = None
        else:
            init_points_df = init_points_df.astype(float)
            init_points = init_points_df.to_dict('list')

        configs = {
            'variables': variables,
            'objectives': objectives,
            'constraints': constraints,
            'states': states,
            'domain_scaling': domain_scaling,
            'tags': tags,
            'init_points': init_points,
        }
        if self.algo_box.check_use_script.isChecked():
            configs['script'] = self.script

        routine = {
            'name': name,
            'algo': algo,
            'env': env,
            'algo_params': algo_params,
            'env_params': env_params,
            'env_vranges': config_list_to_dict(variables),
            'config': configs,
        }


        
        Routine(env, )

        # Sanity check and config normalization
        try:
            routine = normalize_routine(routine)
        except Exception as e:
            raise e

        return routine

    def review(self):
        try:
            routine = self._compose_routine()
        except Exception as e:
            return QMessageBox.critical(self, 'Error!', str(e))

        dlg = BadgerReviewDialog(self, routine)
        dlg.exec()

    def save(self):
        try:
            routine = self._compose_routine()
        except Exception as e:
            return QMessageBox.critical(self, 'Error!', str(e))

        try:
            save_routine(routine)
        except sqlite3.IntegrityError:
            return QMessageBox.critical(self, 'Error!',
                f'Routine {routine["name"]} already existed in the database! Please choose another name.')

        return 0

    def delete(self):
        name = self.edit_save.text() or self.edit_save.placeholderText()
        remove_routine(name)

        return 0
