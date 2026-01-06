"""
Navigator GUI windows for browsing history files and template files.
These windows are displyaed in a tabbed window on the left side of the main Badger GUI.

This file defines the following classes:
- HistoryNavigator: Displays history files in a 'year -> month -> day' file tree.
- TemplateNavigator: Displays template files in tree view.
- FileContextMenuBase: Shared class that adds right-click context menu
  for doing file related actions (open file, open file dir, copy full file path to clipboard).

"""

import os
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QTreeView,
    QTreeWidget,
    QTreeWidgetItem,
    QMenu,
    QAction,
    QApplication,
    QToolTip,
    QFileSystemModel,
)
from PyQt5.QtGui import QFont, QDesktopServices, QCursor
from PyQt5.QtCore import Qt, QUrl, QTimer, QDir
from badger.archive import get_base_run_filename, get_runs
from badger.utils import run_names_to_dict
from badger.settings import init_settings


class FileContextMenuBase:
    """
    Base class that provides context-menu (right-click menu) for Badger's file browser based widgets.
    Adds options to:
      - Open file
      - Open file's containing directory
      - Copy full file path to clipboard
    """

    def show_context_menu(self, widget, fullpath):
        menu = QMenu(widget)
        menu.setStyleSheet("""
        QMenu {
            border: 4px solid yellow;
        }
        """)

        # Functions to execute the context-menu actions
        def copy_fullpath_to_clipboard():
            clip = QApplication.clipboard()
            clip.setText(fullpath)
            # Display a little popup box a bit after user's click
            QTimer.singleShot(
                50,  # ms
                lambda: QToolTip.showText(
                    QCursor.pos(),
                    "Text Copied!",
                    widget,
                ),
            )

        def open_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(fullpath))

        def open_file_location():
            QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.dirname(fullpath)))

        # Add actions to the context menu
        menu.addAction("Open File").triggered.connect(open_file)
        menu.addAction("Open File Directory").triggered.connect(open_file_location)

        # Submenu for copying the full file path
        fullpath_item = QMenu("File Path", menu)
        sub_fullpath_item = QAction(fullpath, fullpath_item)
        sub_fullpath_item.triggered.connect(copy_fullpath_to_clipboard)
        fullpath_item.addAction(sub_fullpath_item)
        menu.addMenu(fullpath_item)

        # Displays menu at curr mouse position
        menu.popup(QCursor.pos())


class HistoryNavigator(QWidget, FileContextMenuBase):
    """
    Navigate through the history files.
    """

    def __init__(self):
        super().__init__()

        # Layout for the widget
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.history_tree_widget = QTreeWidget()

        self.history_tree_widget.setHeaderLabels(["History Navigator"])
        header = self.history_tree_widget.header()
        # Set the font of the header to bold
        bold_font = QFont()
        bold_font.setBold(True)
        header.setFont(bold_font)

        self.history_tree_widget.setMinimumHeight(256)

        self.history_tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.history_tree_widget.customContextMenuRequested.connect(
            self.show_context_menu_history
        )

        layout.addWidget(self.history_tree_widget)

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
            parent = self.history_tree_widget.invisibleRootItem()

        for i in range(parent.childCount()):
            item = parent.child(i)
            if item.flags() & Qt.ItemIsSelectable:
                return item
            result = self._firstSelectableItem(item)
            if result:
                return result
        return None

    def updateItems(self, runs=None):
        self.history_tree_widget.clear()
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
            self.history_tree_widget.addTopLevelItem(item_year)

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
        for i in range(self.history_tree_widget.topLevelItemCount()):
            year_item = self.history_tree_widget.topLevelItem(i)
            for j in range(year_item.childCount()):
                month_item = year_item.child(j)
                for k in range(month_item.childCount()):
                    day_item = month_item.child(k)
                    for _l in range(day_item.childCount()):
                        file_item = day_item.child(_l)
                        if get_base_run_filename(file_item.text(0)) == run:
                            self.history_tree_widget.setCurrentItem(file_item)
                            return

    def currentText(self):
        current_item = self.history_tree_widget.currentItem()
        if current_item:
            return current_item.text(0)
        return ""

    def count(self):
        if self.runs is None:
            return 0

        return len(self.runs)

    def show_context_menu_history(self, position):
        """
        Executed when items in the tree are right-clicked on, and then
        calls the base-class function to actually display the context-menu.
        """
        selected_item = self.history_tree_widget.itemAt(position)
        if selected_item is None:
            return  # user didn't click on any menu item

        # Filename is displayed in gui tree without full path
        run_filename = selected_item.text(0)
        # We need to get the full path to run-file, so we can display it in context menu
        runs = get_runs()
        fullpath = self.find_run_by_name(runs, run_filename)
        if not fullpath:
            return
        filename = os.path.basename(fullpath)
        if not filename.endswith(
            (".yaml", ".yml")
        ):  # To avoid showing context-menu for directories in the tree
            return

        self.show_context_menu(self.history_tree_widget, fullpath)

    def find_run_by_name(self, runs, filename):
        """
        Search in run_list (full paths) for a file matching filename.
        Returns the full path if found, else None.
        """
        for r in runs:
            if os.path.basename(r) == filename:
                return r
        return None


class TemplateNavigator(QWidget, FileContextMenuBase):
    """
    Navigate through the templates
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # get template directory
        config_singleton = init_settings()
        BADGER_PLUGIN_ROOT = config_singleton.read_value("BADGER_PLUGIN_ROOT")
        try:
            self.template_dir = config_singleton.read_value("BADGER_TEMPLATE_ROOT")
        except KeyError:
            self.template_dir = os.path.join(BADGER_PLUGIN_ROOT, "templates")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Tree view + QFileSystemModel
        self.template_tree_view = QTreeView(self)
        layout.addWidget(self.template_tree_view)

        self.template_tree_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.template_tree_view.customContextMenuRequested.connect(
            self.show_context_menu_template
        )

        self.file_sys_model = QFileSystemModel(self)
        self.file_sys_model.setRootPath(self.template_dir)
        self.file_sys_model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Files)

        # Only show YAML files
        self.file_sys_model.setNameFilters(["*.yaml", "*.yml"])
        self.file_sys_model.setNameFilterDisables(False)  # hide non-matching files

        self.template_tree_view.setModel(self.file_sys_model)
        self.template_tree_view.setRootIndex(
            self.file_sys_model.index(self.template_dir)
        )

        self.template_tree_view.setStyleSheet("""
            QTreeView {
                background-color: #37414F;
            }
        """)

        self.template_tree_view.setSortingEnabled(True)  # click headers to sort
        self.template_tree_view.setAnimated(True)
        self.template_tree_view.setHeaderHidden(False)
        self.template_tree_view.setUniformRowHeights(True)  # faster on big trees
        self.template_tree_view.setColumnWidth(0, 200)  # filename column

        # Expand the root for quick glance
        self.template_tree_view.expand(self.file_sys_model.index(self.template_dir))

    def show_context_menu_template(self, position):
        """
        Executed when items in the tree are right-clicked on, and then
        calls the base-class function to actually display the context-menu.
        """
        selected_index = self.template_tree_view.indexAt(position)
        if not selected_index.isValid():
            return  # user didn't click on any menu item

        fullpath = self.template_tree_view.model().filePath(selected_index)
        filename = os.path.basename(fullpath)
        if not filename.endswith(
            (".yaml", ".yml")
        ):  # To avoid showing context-menu for directories in the tree
            return

        self.show_context_menu(self.template_tree_view, fullpath)


# For quick testing (`python src/badger/gui/acr/components/navigators.py`)
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    his_nav = HistoryNavigator()
    his_nav.updateItems(get_runs())
    his_nav.show()
    templ_nav = TemplateNavigator()
    templ_nav.show()
    sys.exit(app.exec())
