"""Searchable table of environment variables from the plugin registry.
Users drag items from here into the variable/observable/constraint tables
when building a routine."""

import logging
from collections.abc import Callable
from typing import Any

from PyQt5.QtCore import (
    QAbstractTableModel,
    QMimeData,
    QModelIndex,
    QObject,
    Qt,
    pyqtSignal,
)
from PyQt5.QtGui import QDrag, QKeyEvent
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from badger.environment import Environment
from badger.errors import BadgerRoutineError

logger = logging.getLogger(__name__)


class ArchiveResultsTableModel(QAbstractTableModel):
    """This table model holds the results of a variable search. This search is for names matching
    the input search words, and the results are a list of variable names that match that search.

    Parameters
    ----------
    parent : QObject, optional
        The parent item of this table
    """

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent=parent)

        self.results_list: list[str] = []
        self.column_names = ("Variable",)

    def rowCount(self, parent: QModelIndex | None = None) -> int:
        """Return the row count of the table"""
        if parent is not None and parent.isValid():
            return 0
        return len(self.results_list)

    def columnCount(self, parent: QModelIndex | None = None) -> int:
        """Return the column count of the table"""
        if parent is not None and parent.isValid():
            return 0
        return len(self.column_names)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        """Return the data for the associated role. Currently only supporting DisplayRole."""
        if not index.isValid():
            return None

        if role != Qt.ItemDataRole.DisplayRole:
            return None

        return self.results_list[index.row()]

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        """Return data associated with the header"""
        if role != Qt.ItemDataRole.DisplayRole:
            return super().headerData(section, orientation, role)

        return str(self.column_names[section])

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Return flags that determine how users can interact with the items in the table"""
        if index.isValid():
            return (
                Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)
                | Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsDragEnabled
            )
        return Qt.ItemFlags()

    def append(self, pv: str) -> None:
        """Appends a row to this table given the variable name as input"""
        self.beginInsertRows(
            QModelIndex(), len(self.results_list), len(self.results_list)
        )
        self.results_list.append(pv)
        self.endInsertRows()
        self.layoutChanged.emit()

    def replace_rows(self, pvs: list[str]) -> None:
        """Overwrites any existing rows in the table with the input list of variable names"""
        self.beginInsertRows(QModelIndex(), 0, len(pvs) - 1)
        self.results_list = pvs
        self.endInsertRows()
        self.layoutChanged.emit()

    def clear(self) -> None:
        """Clear out all data stored in this table"""
        self.beginRemoveRows(QModelIndex(), 0, len(self.results_list))
        self.results_list = []
        self.endRemoveRows()
        self.layoutChanged.emit()

    def sort(self, col: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder) -> None:
        """Sort the table by variable name"""
        self.results_list.sort(reverse=order == Qt.SortOrder.DescendingOrder)
        self.layoutChanged.emit()


class ResultsTableView(QTableView):
    """Table view whose drag payload is the caller-supplied selected-variable text."""

    def __init__(
        self,
        get_selected: Callable[[], str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._get_selected = get_selected

    def startDrag(self, supportedActions: Qt.DropActions | Qt.DropAction) -> None:
        """Start a drag carrying the selected variable names so they can be dropped
        onto a plot to begin drawing that variable's data."""
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self._get_selected())
        drag.setMimeData(mime_data)
        drag.exec_()


class ArchiveSearchWidget(QWidget):
    """
    The ArchiveSearchWidget is a display widget for showing the results of a variable search using, for example, an instance of the
    EPICS archiver appliance. Currently the only type of search supported is for variable names matching an input search
    string, though this can be extended in the future.

    Parameters
    ----------
    parent : QWidget, optional
        The parent widget of this widget
    """

    append_variables_requested = pyqtSignal(str)

    def __init__(self, environment: Environment, parent: QWidget | None = None) -> None:
        super().__init__(parent=parent)
        self.env = environment

        self.resize(400, 800)
        self.setWindowTitle("Variable Search")
        self._layout = QVBoxLayout()

        self.search_label = QLabel("Pattern")
        self.search_box = QLineEdit()
        self.search_button = QPushButton("Search")
        self.search_button.setFixedSize(96, 24)
        self.search_button.setDefault(True)
        self.search_button.clicked.connect(self.request_variable_search)

        self.loading_label = QLabel("Loading...")
        self.loading_label.hide()

        self.results_table_model = ArchiveResultsTableModel()
        self.results_view = ResultsTableView(self.selectedVariables, self)
        self.results_view.setModel(self.results_table_model)
        self.results_view.setProperty("showDropIndicator", False)
        self.results_view.setDragDropOverwriteMode(False)
        self.results_view.setDragEnabled(True)
        self.results_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.results_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_view.setDropIndicatorShown(True)
        self.results_view.setCornerButtonEnabled(False)
        self.results_view.setSortingEnabled(True)
        vheader = self.results_view.verticalHeader()
        if vheader is not None:
            vheader.setVisible(False)
        hheader = self.results_view.horizontalHeader()
        if hheader is not None:
            hheader.setSectionResizeMode(QHeaderView.Stretch)

        self.archive_url_layout = QHBoxLayout()
        self._layout.addLayout(self.archive_url_layout)
        self.search_layout = QHBoxLayout()
        self.search_layout.addWidget(self.search_label)
        self.search_layout.addWidget(self.search_box)
        self.search_layout.addWidget(self.search_button)
        self._layout.addLayout(self.search_layout)
        self._layout.addWidget(self.loading_label)
        self._layout.addWidget(self.results_view)
        self.results_view.doubleClicked.connect(
            lambda: self.append_variables_requested.emit(self.selectedVariables())
        )
        self.setLayout(self._layout)

    def selectedVariables(self) -> str:
        """Figure out based on which indexes were selected, the list of variables (by string name)
        The user was hoping to insert into the table. Concatenate them into string form i.e.
        <v1>, <v2>, <v3>"""
        indices = self.results_view.selectedIndexes()
        pv_list = ""
        for index in indices:
            pv_name = self.results_table_model.results_list[index.row()]
            pv_list += pv_name + ", "
        return pv_list[:-2]

    def keyPressEvent(self, e: QKeyEvent | None) -> None:
        """Special key press tracker, just so that if enter or return is pressed the formula dialog attempts to submit the formula"""
        if e is not None and (
            e.key() == Qt.Key.Key_Return or e.key() == Qt.Key.Key_Enter
        ):
            self.request_variable_search()
        return super().keyPressEvent(e)

    def request_variable_search(self) -> None:
        """
        Process the search input and initiate a variable search.

        This method retrieves the search text from the search box, replaces any
        question marks with a period to normalize the input, and then performs a
        variable search using the environment's search method. While waiting for the
        search results, a loading indicator is shown. Once the reply is received,
        the results list is populated accordingly.

        Returns
        -------
        None
        """
        search_text = self.search_box.text()
        search_text = search_text.replace("?", ".")
        self.loading_label.show()
        self.env.search(search_text, self.populate_results_list)

    def populate_results_list(self, reply: list[str]) -> None:
        """
        Update the results table with new search results.

        This callback is called when new search results (a list of strings) are available.
        It hides the loading indicator, clears any existing rows in the results table model, and replaces them with the new results.

        Parameters
        ----------
        reply : list[str]
            A list of search result strings to be displayed in the table.

        Raises
        ------
        BadgerRoutineError
            If the reply is empty or None, indicating that no search results could be retrieved.
        """
        self.loading_label.hide()

        if reply:
            self.results_table_model.clear()
            self.results_table_model.replace_rows(reply)
        else:
            raise BadgerRoutineError("Could not retrieve search results")
