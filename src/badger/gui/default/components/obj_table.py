from PyQt5.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QStyledItemDelegate,
)


class ObjectiveTable(QTableWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Reorder the rows by dragging around
        # self.setSelectionBehavior(self.SelectRows)
        # self.setSelectionMode(self.SingleSelection)
        # self.setShowGrid(False)
        # self.setDragDropMode(self.InternalMove)
        # self.setDragDropOverwriteMode(False)

        self.setRowCount(0)
        self.setColumnCount(3)
        self.setAlternatingRowColors(True)
        self.setStyleSheet("alternate-background-color: #262E38;")
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        self.setColumnWidth(0, 20)
        self.setColumnWidth(2, 192)

        self.all_objectives = []
        self.objectives = []
        self.selected = {}  # track obj selected status
        self.rules = {}  # track obj rules
        self.checked_only = False

        self.config_logic()

    def config_logic(self):
        self.horizontalHeader().sectionClicked.connect(self.header_clicked)

    def is_all_checked(self):
        for i in range(self.rowCount()):
            item = self.cellWidget(i, 0)
            if not item.isChecked():
                return False

        return True

    def header_clicked(self, idx):
        if idx:
            return

        all_checked = self.is_all_checked()

        for i in range(self.rowCount()):
            item = self.cellWidget(i, 0)
            # Doing batch update
            item.blockSignals(True)
            item.setChecked(not all_checked)
            item.blockSignals(False)
        self.update_selected(0)

    def update_rules(self):
        for i in range(self.rowCount()):
            name = self.item(i, 1).text()
            rule = self.cellWidget(i, 2)
            self.rules[name] = rule.currentText()

    def set_rules(self, objectives):
        for name in objectives:
            self.rules[name] = objectives[name]

        self.update_objectives(self.objectives, 2)

    def update_selected(self, _):
        for i in range(self.rowCount()):
            _cb = self.cellWidget(i, 0)
            name = self.item(i, 1).text()
            self.selected[name] = _cb.isChecked()

        if self.checked_only:
            self.show_checked_only()

    def set_selected(self, objective_names):
        self.selected = {}
        for oname in objective_names:
            self.selected[oname] = True

        self.update_objectives(self.objectives, 2)

    def toggle_show_mode(self, checked_only):
        self.checked_only = checked_only
        if checked_only:
            self.show_checked_only()
        else:
            self.show_all()

    def show_checked_only(self):
        checked_objectives = []
        for obj in self.objectives:
            name = next(iter(obj))
            if self.is_checked(name):
                checked_objectives.append(obj)
        self.update_objectives(checked_objectives, 2)

    def show_all(self):
        self.update_objectives(self.objectives, 2)

    def is_checked(self, name):
        try:
            _checked = self.selected[name]
        except KeyError:
            _checked = False

        return _checked

    def update_objectives(self, objectives, filtered=0):
        # filtered = 0: completely refresh
        # filtered = 1: filtered by keyword
        # filtered = 2: just rerender based on check status

        self.setRowCount(0)
        self.horizontalHeader().setVisible(False)

        if not filtered:
            self.all_objectives = objectives or []
            self.objectives = self.all_objectives
            self.selected = {}
            self.rules = {}
            for obj in self.objectives:
                name = next(iter(obj))
                self.rules[name] = obj[name]
        elif filtered == 1:
            self.objectives = objectives or []

        if not objectives:
            return

        _objectives = []
        if self.checked_only:
            for obj in objectives:
                name = next(iter(obj))
                if self.is_checked(name):
                    _objectives.append(obj)
        else:
            _objectives = objectives

        n = len(_objectives)
        self.setRowCount(n)
        for i, obj in enumerate(_objectives):
            name = next(iter(obj))

            self.setCellWidget(i, 0, QCheckBox())

            _cb = self.cellWidget(i, 0)
            _cb.setChecked(self.is_checked(name))
            _cb.stateChanged.connect(self.update_selected)
            self.setItem(i, 1, QTableWidgetItem(name))

            _rule = self.rules[name]
            cb_rule = QComboBox()
            cb_rule.setItemDelegate(QStyledItemDelegate())
            cb_rule.addItems(["MINIMIZE", "MAXIMIZE"])
            cb_rule.setCurrentIndex(0 if _rule == "MINIMIZE" else 1)
            cb_rule.currentIndexChanged.connect(self.update_rules)
            self.setCellWidget(i, 2, cb_rule)

        self.setHorizontalHeaderLabels(["", "Name", "Rule"])
        self.setVerticalHeaderLabels([str(i) for i in range(n)])

        header = self.horizontalHeader()
        header.setVisible(True)

    def export_objectives(self):
        objectives_exported = {}
        for obj in self.all_objectives:
            name = next(iter(obj))
            if self.is_checked(name):
                objectives_exported[name] = self.rules[name]

        return objectives_exported
