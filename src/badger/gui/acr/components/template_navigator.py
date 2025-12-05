# badger/gui/acr/components/templates_tab.py
import os
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTreeView, QFileSystemModel
from PyQt5.QtCore import QDir
from badger.settings import init_settings


class TemplateNavigator(QWidget):
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
        self.tree_view = QTreeView(self)
        layout.addWidget(self.tree_view)

        self.file_sys_model = QFileSystemModel(self)
        self.file_sys_model.setRootPath(self.template_dir)
        self.file_sys_model.setFilter(QDir.AllDirs | QDir.NoDotAndDotDot | QDir.Files)

        # Only show YAML files
        self.file_sys_model.setNameFilters(["*.yaml", "*.yml"])
        self.file_sys_model.setNameFilterDisables(False)  # hide non-matching files

        self.tree_view.setModel(self.file_sys_model)
        self.tree_view.setRootIndex(self.file_sys_model.index(self.template_dir))

        self.tree_view.setStyleSheet("""
            QTreeView {
                background-color: #37414F;
            }
        """)

        self.tree_view.setSortingEnabled(True)  # click headers to sort
        self.tree_view.setAnimated(True)
        self.tree_view.setHeaderHidden(False)
        self.tree_view.setUniformRowHeights(True)  # faster on big trees
        self.tree_view.setColumnWidth(0, 200)  # filename column

        # Expand the root for quick glance
        self.tree_view.expand(self.file_sys_model.index(self.template_dir))
