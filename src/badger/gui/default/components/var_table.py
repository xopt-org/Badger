from qtpy.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QCheckBox,
    QMessageBox,
    QAbstractItemView,
)
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QColor
from badger.gui.default.components.robust_spinbox import RobustSpinBox

from badger.environment import instantiate_env
from badger.errors import BadgerInterfaceChannelError


class VariableTable(QTableWidget):
    sig_sel_changed = Signal()
    sig_pv_added = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)

        # Reorder the rows by dragging around
        # self.setSelectionBehavior(self.SelectRows)
        # self.setSelectionMode(self.SingleSelection)
        # self.setShowGrid(False)
        # self.setDragDropMode(self.InternalMove)
        # self.setDragDropOverwriteMode(False)

        self.setRowCount(0)
        self.setColumnCount(4)
        self.setAlternatingRowColors(True)
        self.setStyleSheet("alternate-background-color: #262E38;")
        # self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        # header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        # header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        # header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.setColumnWidth(0, 20)
        self.setColumnWidth(2, 96)
        self.setColumnWidth(3, 96)

        self.all_variables = []  # store all variables
        self.variables = []  # store variables to be displayed
        self.selected = {}  # track var selected status
        self.bounds = {}  # track var bounds
        self.checked_only = False
        self.bounds_locked = False
        self.addtl_vars = []  # track variables added on the fly
        self.env_class = None  # needed to get bounds on the fly
        self.env = None  # needed to get bounds on the fly
        self.configs = None  # needed to get bounds on the fly
        self.previous_values = {}  # to track changes in table
        self.config_logic()

    def config_logic(self):
        self.horizontalHeader().sectionClicked.connect(self.header_clicked)
        # Catch if any item gets changed
        self.itemChanged.connect(self.add_additional_variable)

    def setItem(self, row, column, item):
        text = item.text()
        if text != "Enter new variable here....":
            self.previous_values[(row, column)] = item.text()
        super().setItem(row, column, item)

    def is_all_checked(self):
        for i in range(self.rowCount() - 1):
            item = self.cellWidget(i, 0)
            if not item.isChecked():
                return False

        return True

    def header_clicked(self, idx):
        if idx:
            return

        all_checked = self.is_all_checked()

        for i in range(self.rowCount() - 1):
            item = self.cellWidget(i, 0)
            # Doing batch update
            item.blockSignals(True)
            item.setChecked(not all_checked)
            item.blockSignals(False)
        self.update_selected(0)

    def update_bounds(self):
        for i in range(self.rowCount() - 1):
            name = self.item(i, 1).text()
            sb_lower = self.cellWidget(i, 2)
            sb_upper = self.cellWidget(i, 3)
            self.bounds[name] = [sb_lower.value(), sb_upper.value()]

    def set_bounds(self, variables: dict, signal=True):
        for name in variables:
            self.bounds[name] = variables[name]

        if signal:
            self.update_variables(self.variables, 2)
        else:
            self.update_variables(self.variables, 3)

    def update_selected(self, _):
        for i in range(self.rowCount() - 1):
            _cb = self.cellWidget(i, 0)
            name = self.item(i, 1).text()
            if name != "Enter new variable here....":  # TODO: fix...
                self.selected[name] = _cb.isChecked()

        self.sig_sel_changed.emit()

        if self.checked_only:
            self.show_checked_only()

    def set_selected(self, variable_names):
        self.selected = {}
        for vname in variable_names:
            self.selected[vname] = True

        self.update_variables(self.variables, 2)

    def toggle_show_mode(self, checked_only):
        self.checked_only = checked_only
        if checked_only:
            self.show_checked_only()
        else:
            self.show_all()

    def show_checked_only(self):
        checked_variables = []
        for var in self.variables:
            name = next(iter(var))
            if self.is_checked(name):
                checked_variables.append(var)
        self.update_variables(checked_variables, 2)

    def show_all(self):
        self.update_variables(self.variables, 2)

    def is_checked(self, name):
        try:
            _checked = self.selected[name]
        except KeyError:
            _checked = False

        return _checked

    def update_variables(self, variables, filtered=0):
        # filtered = 0: completely refresh
        # filtered = 1: filtered by keyword
        # filtered = 2: just rerender based on check status
        # filtered = 3: same as 2 but do not emit the signal

        self.setRowCount(0)
        self.horizontalHeader().setVisible(False)

        if not filtered:
            self.all_variables = variables or []
            self.variables = self.all_variables[:]  # make a copy
            self.selected = {}
            self.bounds = {}
            self.addtl_vars = []
            for var in self.variables:
                name = next(iter(var))
                self.bounds[name] = var[name]
        elif filtered == 1:
            self.variables = variables or []

        if not variables:
            return

        _variables = []
        if self.checked_only:
            for var in variables:
                name = next(iter(var))
                if self.is_checked(name):
                    _variables.append(var)
        else:
            _variables = variables

        n = len(_variables) + 1
        self.setRowCount(n)
        self.previous_values = {}  # to track changes in table

        for i, var in enumerate(_variables):
            name = next(iter(var))
            vrange = var[name]

            self.setCellWidget(i, 0, QCheckBox())

            _cb = self.cellWidget(i, 0)
            _cb.setChecked(self.is_checked(name))
            _cb.stateChanged.connect(self.update_selected)
            item = QTableWidgetItem(name)
            if name in self.addtl_vars:
                # Make new PVs a different color
                item.setForeground(QColor("darkCyan"))
            else:
                # Make non-new PVs not editable
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            self.setItem(i, 1, item)

            _bounds = self.bounds[name]
            sb_lower = RobustSpinBox(
                default_value=_bounds[0], lower_bound=vrange[0], upper_bound=vrange[1]
            )
            sb_lower.valueChanged.connect(self.update_bounds)
            sb_upper = RobustSpinBox(
                default_value=_bounds[1], lower_bound=vrange[0], upper_bound=vrange[1]
            )
            sb_upper.valueChanged.connect(self.update_bounds)
            self.setCellWidget(i, 2, sb_lower)
            self.setCellWidget(i, 3, sb_upper)

            if self.bounds_locked:
                sb_lower.setEnabled(False)
                sb_upper.setEnabled(False)
            else:
                sb_lower.setEnabled(True)
                sb_upper.setEnabled(True)

        # Make extra editable row
        item = QTableWidgetItem("Enter new variable here....")
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        item.setForeground(QColor("gray"))
        self.setItem(n - 1, 1, item)

        self.setHorizontalHeaderLabels(["", "Name", "Min", "Max"])
        self.setVerticalHeaderLabels([str(i) for i in range(n)])

        header = self.horizontalHeader()
        # header.setSectionResizeMode(0, QHeaderView.Interactive)
        header.setVisible(True)

        if filtered != 3:
            self.sig_sel_changed.emit()

    def add_additional_variable(self, item):
        row = idx = item.row()
        column = item.column()
        name = item.text()

        if (
            row != self.rowCount() - 1
            and column == 1
            and name != "Enter new variable here...."
        ):
            # check that the new text is not equal to the previous value at that cell
            prev_name = self.previous_values.get((row, column), "")
            if name == prev_name:
                return
            else:
                # delete row and additional variable
                self.removeRow(row)
                self.addtl_vars.remove(prev_name)
                self.variables = [
                    var for var in self.variables if next(iter(var)) != prev_name
                ]
                del self.bounds[prev_name]
                del self.selected[prev_name]

                self.update_variables(self.variables, 2)
            return

        if (
            row == self.rowCount() - 1
            and column == 1
            and name != "Enter new variable here...."
        ):
            # Check that variables doesn't already exist in table
            if name in [list(d.keys())[0] for d in self.variables]:
                self.update_variables(self.variables, 2)
                QMessageBox.warning(
                    self, "Variable already exists!", f"Variable {name} already exists!"
                )
                return

            # Get bounds from interface, if PV exists on interface
            _bounds = None
            if self.env_class is not None:
                try:
                    _, _bounds = self.get_bounds(name)
                    vrange = _bounds
                except BadgerInterfaceChannelError:
                    # Raised when PV does not exist after attempting to call value
                    # Revert table to previous state
                    self.update_variables(self.variables, 2)
                    QMessageBox.critical(
                        self,
                        "Variable Not Found!",
                        f"Variable {name} cannot be found through the interface!",
                    )
                    return
                # except Exception as e: # TODO: fix this
                #     print(e)
                #     # Raised when PV exists but value/hard limits cannot be found
                #     # Set to some default values
                #     _bounds = vrange = [-1, 1]
                #     QMessageBox.warning(self, 'Bounds could not be found!',
                #                         f'Variable {name} bounds could not be found.' +
                #                         'Please check default values!'
                #                         )
            else:
                # TODO: handle this case? Right now I don't think it should happen
                raise "Environment cannot be found for new variable bounds!"

            # Add checkbox only when a PV is entered
            self.setCellWidget(idx, 0, QCheckBox())

            _cb = self.cellWidget(idx, 0)

            # Checked by default when entered
            _cb.setChecked(True)
            self.selected[name] = True

            _cb.stateChanged.connect(self.update_selected)

            sb_lower = RobustSpinBox(
                default_value=_bounds[0], lower_bound=vrange[0], upper_bound=vrange[1]
            )
            sb_lower.valueChanged.connect(self.update_bounds)
            sb_upper = RobustSpinBox(
                default_value=_bounds[1], lower_bound=vrange[0], upper_bound=vrange[1]
            )
            sb_upper.valueChanged.connect(self.update_bounds)
            self.setCellWidget(idx, 2, sb_lower)
            self.setCellWidget(idx, 3, sb_upper)

            self.add_variable(name, vrange[0], vrange[1])
            self.addtl_vars.append(name)

            self.update_variables(self.variables, 2)

            self.sig_pv_added.emit()  # notify the routine page that a new PV has been added

    def get_bounds(self, name):
        # TODO: move elsewhere?
        self.env = instantiate_env(self.env_class, self.configs)

        value = self.env.get_variable(name)
        bound = self.env._get_bounds([name])[name]
        return value, bound

    def add_variable(self, name, lb, ub):
        var = {name: [lb, ub]}

        self.all_variables.append(var)
        self.variables.append(var)
        self.bounds[name] = [lb, ub]

    def export_variables(self) -> dict:
        variables_exported = {}
        for var in self.all_variables:
            name = next(iter(var))
            if self.is_checked(name):
                variables_exported[name] = self.bounds[name]

        return variables_exported

    def lock_bounds(self):
        self.bounds_locked = True
        self.toggle_show_mode(self.checked_only)

    def unlock_bounds(self):
        self.bounds_locked = False
        self.toggle_show_mode(self.checked_only)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            text = event.mimeData().text()
            strings = text.strip().split("\n")

            position = event.pos()
            drop_row = self.rowAt(position.y())
            if drop_row == -1:
                drop_row = self.rowCount()

            for i, string in enumerate(strings):
                string = string.strip()
                if not string:
                    continue

                row = drop_row + i
                if row >= self.rowCount():
                    self.insertRow(row)

                item = QTableWidgetItem(string)
                self.setItem(row, 1, item)

                self.add_additional_variable(item)

            event.acceptProposedAction()
        else:
            event.ignore()

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if index.column() == 1:
            flags |= Qt.ItemIsEditable | Qt.ItemIsDropEnabled
        return flags
