from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
from badger.archive import get_base_run_filename
from badger.utils import run_names_to_dict


class HistoryNavigator(QWidget):
    def __init__(self):
        super().__init__()

        # Layout for the widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tree_widget = QTreeWidget()

        self.tree_widget.setHeaderLabels(["History Navigator"])
        header = self.tree_widget.header()
        # Set the font of the header to bold
        bold_font = QFont()
        bold_font.setBold(True)
        header.setFont(bold_font)

        self.tree_widget.setMinimumHeight(256)
        layout.addWidget(self.tree_widget)

        self.runs = None  # all runs to be shown in the tree widget
        self.setStyleSheet("""
            QTreeWidget {
                background-color: #37414F;
            }
        """)

    def _firstSelectableItem(self, parent=None):
        """
        Internal recursive function for finding the first selectable item.
        """
        if parent is None:
            parent = self.tree_widget.invisibleRootItem()

        for i in range(parent.childCount()):
            item = parent.child(i)
            if item.flags() & Qt.ItemIsSelectable:
                return item
            result = self._firstSelectableItem(item)
            if result:
                return result
        return None

    def updateItems(self, runs=None):
        self.tree_widget.clear()
        self.runs = runs  # store the runs for navigation
        if runs is None:
            return

        runs_dict = run_names_to_dict(runs)
        first_items = []
        flag_first_item = True

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

                    for file in list_day:
                        item_file = QTreeWidgetItem([file])
                        item_day.addChild(item_file)
                    item_month.addChild(item_day)
                item_year.addChild(item_month)
            self.tree_widget.addTopLevelItem(item_year)

        # Expand the first set of items
        for item in first_items:
            item.setExpanded(True)

    def selectNextItem(self):
        run_curr = get_base_run_filename(self.currentText())
        idx = self.runs.index(run_curr)
        if idx < len(self.runs) - 1:
            self._selectItemByRun(self.runs[idx + 1])

    def selectPreviousItem(self):
        run_curr = get_base_run_filename(self.currentText())
        idx = self.runs.index(run_curr)
        if idx > 0:
            self._selectItemByRun(self.runs[idx - 1])

    def _selectItemByRun(self, run):
        """
        Internal function to select a tree widget item by run name.
        """
        for i in range(self.tree_widget.topLevelItemCount()):
            year_item = self.tree_widget.topLevelItem(i)
            for j in range(year_item.childCount()):
                month_item = year_item.child(j)
                for k in range(month_item.childCount()):
                    day_item = month_item.child(k)
                    for _l in range(day_item.childCount()):
                        file_item = day_item.child(_l)
                        if get_base_run_filename(file_item.text(0)) == run:
                            self.tree_widget.setCurrentItem(file_item)
                            return

    def currentText(self):
        current_item = self.tree_widget.currentItem()
        if current_item:
            return current_item.text(0)
        return ""

    def count(self):
        if self.runs is None:
            return 0

        return len(self.runs)
