from PyQt5.QtWidgets import (
    QHBoxLayout,
    QVBoxLayout,
    QCheckBox,
    QWidget,
    QMainWindow,
    QTextBrowser,
)
from badger.factory import load_badger_docs, load_plugin_docs, list_generators
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PyQt5.QtCore import QUrl


class BadgerDocsWindow(QMainWindow):
    def __init__(self, parent, name: str = "", plugin_type: str = ""):
        """
        Docs window for displaying badger documentation. Can be used to display general
        badger documentation (if no plugin_type is provided) or, to display documentation
        for a specific plugin, provide the plugin_type (e.g. "environment") which should
        match the subdirectory (minus the 's') in which the plugin is located.

        Parameters
        ----------
        parent : QWidget
            The parent widget for this window
        name : str, optional
            The name of the docs to load. Optional on initialization
        plugin_type : str, optional
            The type of plugin to load docs for. If not provided, the window will load docs
            from the general badger documentation directory (Badger/documentation/docs) rather
            than a specific plugin (from the BADGER_PLUGIN_ROOT)
        """
        super().__init__(parent=parent)

        self.docs_name = name
        self.docs = ""
        self.plugin_type = plugin_type

        self.init_ui()
        self.config_logic()
        self.load_docs()

    def init_ui(self):
        self.setWindowTitle(f"Docs for {self.docs_name}")
        self.resize(640, 640)

        doc_panel = QWidget(self)
        vbox = QVBoxLayout(doc_panel)

        # Toolbar
        toolbar = QWidget()
        hbox_tool = QHBoxLayout(toolbar)
        hbox_tool.setContentsMargins(0, 0, 0, 0)
        self.cb_md = cb_md = QCheckBox("Render as Markdown")
        cb_md.setChecked(True)
        hbox_tool.addStretch()
        hbox_tool.addWidget(cb_md)
        vbox.addWidget(toolbar)

        self.markdown_viewer = QTextBrowser()
        vbox.addWidget(self.markdown_viewer)

        self.setCentralWidget(doc_panel)

    def config_logic(self):
        self.cb_md.stateChanged.connect(self.refresh_docs_view)
        self.markdown_viewer.anchorClicked.connect(self.handle_link_click)

    def load_docs(self, subdir: str = None):
        """
        Load the docs for the current generator and subdir (if provided).

        Parameters
        ----------
        subdir : str, optional
            The subdirectory to load docs from, relatve to 'documentation' / 'docs' / 'guides'
        """
        try:
            if self.plugin_type == "":
                # Load general badger documentation from the docs directory
                self.docs = load_badger_docs(self.docs_name, subdir)
            else:
                # Load plugin documentation from plugin root
                self.docs = load_plugin_docs(self.docs_name, self.plugin_type)
        except Exception as e:
            self.docs = str(e)

        self.refresh_docs_view()

    def update_docs(self, name: str, doctype: str = ""):
        """
        Update selected docs and refresh the window with the new docs

        Parameters
        ----------
        name : str
            The name of the file to load docs for
        subdir : str, optional
            The subdirectory in which the file is located
        """
        self.docs_name = name
        self.setWindowTitle(f"Docs for {doctype.title()} {name}")
        self.load_docs(doctype)

    def handle_link_click(self, url: "QUrl") -> None:
        """
        Handle links from the markdown viewer. Parses the url and loads the
        corresponding docs.

        Parameters
        ----------
        url : QUrl
            The url that was clicked. Expected format is /<name>#<subdir>
        """
        # format url to string
        href = url.toString()

        # Indicate links not yet supported in GUI docs viewer
        if href.startswith("https://") or href.startswith("mailto:"):
            self.docs_name = "external links not yet implemented in GUI docs viewer"
            self.load_docs()
            return

        url_end = href.split("/")[-1].split("#")

        self.docs_name = url_end[0]

        # Check if the docs correspond to a generator,
        # if so set the ptype so that the correct directory
        # is searched and docstring is added
        if self.plugin_type:
            ptype = self.plugin_type
        elif self.docs_name in self.generator_list:
            ptype = "generator"
        else:
            ptype = ""

        self.update_docs(name=self.docs_name, doctype=ptype)

    def refresh_docs_view(self):
        if self.cb_md.isChecked():
            self.markdown_viewer.setMarkdown(self.docs)
        else:
            self.markdown_viewer.setText(self.docs)

    @property
    def generator_list(self):
        if not hasattr(self, "_generator_list"):
            self._generator_list = list_generators()
        return self._generator_list
