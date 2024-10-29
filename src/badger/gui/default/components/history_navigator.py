from PyQt5.QtWidgets import QComboBox, QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import QModelIndex, Qt
from badger.archive import get_base_run_filename
from badger.utils import run_names_to_dict


# Modified based on the following solution
# https://stackoverflow.com/a/9672359/4263605
class HistoryNavigator(QComboBox):
    def __init__(self):
        super().__init__()
        # self.view() = QTreeWidget()
        self.setView(QTreeWidget())
        self.setModel(self.view().model())

        self.view().setHeaderHidden(True)
        self.view().setMinimumHeight(256)
        # self.view().setItemsExpandable(False)
        # self.view().setRootIsDecorated(False)
        self.runs = None  # all runs to be shown in combobox

    def showPopup(self):
        self.setRootModelIndex(QModelIndex())  # key to success!
        QComboBox.showPopup(self)

    def _firstSelectableItem(self, parent=QModelIndex()):
        """
        Internal recursive function for finding the first selectable item.
        """
        for i in range(self.model().rowCount(parent)):
            itemIndex = self.model().index(i, 0, parent)
            if self.view().itemFromIndex(itemIndex).flags() & Qt.ItemIsSelectable:
                return parent, i
            else:
                itemIndex, row = self._firstSelectableItem(itemIndex)
                if row is not None:
                    return itemIndex, row
        return parent, None

    def currentIsFirst(self):
        if not self.runs:
            return True

        run = get_base_run_filename(self.currentText())
        try:
            idx = self.runs.index(run)
            if idx == 0:
                return True
            else:
                return False
        except:  # run is empty string
            return True

    def currentIsLast(self):
        if not self.runs:
            return True

        run = get_base_run_filename(self.currentText())
        try:
            idx = self.runs.index(run)
            tot = len(self.runs)
            if idx == tot - 1:
                return True
            else:
                return False
        except:  # run is empty string
            return True

    def _firstMatchingSelectableItem(self, text, parent=QModelIndex()):
        for i in range(self.model().rowCount(parent)):
            itemIndex = self.model().index(i, 0, parent)
            item = self.view().itemFromIndex(itemIndex)
            if (item.flags() & Qt.ItemIsSelectable) and item.text(0).startswith(text):
                return parent, i
            else:
                itemIndex, row = self._firstMatchingSelectableItem(text, itemIndex)
                if row is not None:
                    return itemIndex, row
        return parent, None

    def _nextSelectableItem(self, parent=QModelIndex()):
        run_curr = get_base_run_filename(self.currentText())
        idx = self.runs.index(run_curr)
        run_next = self.runs[idx + 1]

        return self._firstMatchingSelectableItem(run_next)

    def _previousSelectableItem(self, parent=QModelIndex()):
        run_curr = get_base_run_filename(self.currentText())
        idx = self.runs.index(run_curr)
        run_prev = self.runs[idx - 1]

        return self._firstMatchingSelectableItem(run_prev)

    def _currentSelectableItem(self, parent=QModelIndex()):
        run_curr = get_base_run_filename(self.currentText())

        return self._firstMatchingSelectableItem(run_curr)

    def updateItems(self, runs=None):
        self.view().clear()

        self.runs = runs  # store the runs for nav
        if runs is None:
            return

        items = []
        flag_first_item = True
        first_items = []
        runs_dict = run_names_to_dict(runs)
        for year, dict_year in runs_dict.items():
            item_year = QTreeWidgetItem([year])
            item_year.setFlags(item_year.flags() & ~Qt.ItemIsSelectable)

            if flag_first_item:
                first_items.append(item_year)

            for month, dict_month in dict_year.items():
                item_month = QTreeWidgetItem([month])
                item_month.setFlags(item_month.flags() & ~Qt.ItemIsSelectable)

                if flag_first_item:
                    first_items.append(item_month)

                for day, list_day in dict_month.items():
                    item_day = QTreeWidgetItem([day])
                    item_day.setFlags(item_day.flags() & ~Qt.ItemIsSelectable)

                    if flag_first_item:
                        first_items.append(item_day)
                        flag_first_item = False

                    for i, file in enumerate(list_day):
                        item_file = QTreeWidgetItem([file])
                        item_day.addChild(item_file)
                    item_month.addChild(item_day)
                item_year.addChild(item_month)
            items.append(item_year)
        self.view().insertTopLevelItems(0, items)
        for item in first_items:
            item.setExpanded(True)

        parent, row = self._firstSelectableItem()  # key to success!
        if row is not None:
            self.setRootModelIndex(parent)
            self.setCurrentIndex(row)

    def selectNextItem(self):
        parent, row = self._nextSelectableItem()
        if row is not None:
            self.setRootModelIndex(parent)
            self.setCurrentIndex(row)

    def selectPreviousItem(self):
        parent, row = self._previousSelectableItem()
        if row is not None:
            self.setRootModelIndex(parent)
            self.setCurrentIndex(row)

    def changeCurrentItem(self, text, color=None):
        parent, row = self._currentSelectableItem()
        if row is not None:
            itemIndex = self.model().index(row, 0, parent)
            item = self.view().itemFromIndex(itemIndex)
            item.setText(0, text)
            if color:
                item.setForeground(0, color)
