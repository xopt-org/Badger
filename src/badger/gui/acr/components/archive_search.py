import logging
from typing import List
from PyQt5.QtGui import QDrag, QKeyEvent
from PyQt5.QtCore import (
    QAbstractTableModel,
    QMimeData,
    QModelIndex,
    QObject,
    Qt,
    QVariant,
    pyqtSignal,
)
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkReply
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

logger = logging.getLogger(__name__)


class ArchiveResultsTableModel(QAbstractTableModel):
    """This table model holds the results of an archiver appliance PV search. This search is for names matching
    the input search words, and the results are a list of PV names that match that search.

    Parameters
    ----------
    parent : QObject, optional
        The parent item of this table
    """

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent=parent)

        self.results_list = []
        self.column_names = ("Variable",)

    def rowCount(self, parent: QObject) -> int:
        """Return the row count of the table"""
        if parent is not None and parent.isValid():
            return 0
        return len(self.results_list)

    def columnCount(self, parent: QObject) -> int:
        """Return the column count of the table"""
        if parent is not None and parent.isValid():
            return 0
        return len(self.column_names)

    def data(self, index: QModelIndex, role: int) -> QVariant:
        """Return the data for the associated role. Currently only supporting DisplayRole."""
        if not index.isValid():
            return QVariant()

        if role != Qt.DisplayRole:
            return QVariant()

        return self.results_list[index.row()]

    def headerData(self, section, orientation, role=Qt.DisplayRole) -> QVariant:
        """Return data associated with the header"""
        if role != Qt.DisplayRole:
            return super().headerData(section, orientation, role)

        return str(self.column_names[section])

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """Return flags that determine how users can interact with the items in the table"""
        if index.isValid():
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled

    def append(self, pv: str) -> None:
        """Appends a row to this table given the PV name as input"""
        self.beginInsertRows(
            QModelIndex(), len(self.results_list), len(self.results_list)
        )
        self.results_list.append(pv)
        self.endInsertRows()
        self.layoutChanged.emit()

    def replace_rows(self, pvs: List[str]) -> None:
        """Overwrites any existing rows in the table with the input list of PV names"""
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

    def sort(self, col: int, order=Qt.AscendingOrder) -> None:
        """Sort the table by PV name"""
        self.results_list.sort(reverse=order == Qt.DescendingOrder)
        self.layoutChanged.emit()


class ArchiveSearchWidget(QWidget):
    """
    The ArchiveSearchWidget is a display widget for showing the results of a PV search using an instance of the
    EPICS archiver appliance. Currently the only type of search supported is for PV names matching an input search
    string, though this can be extended in the future.

    Parameters
    ----------
    parent : QObject, optional
        The parent item of this widget
    """

    append_PVs_requested = pyqtSignal(str)

    def __init__(self, environment, parent: QObject = None) -> None:
        super().__init__(parent=parent)
        self.env = environment
        self.network_manager = QNetworkAccessManager()
        self.network_manager.finished.connect(self.populate_results_list)

        self.resize(400, 800)
        self.layout = QVBoxLayout()

        # self.archive_title_label = QLabel("Archive URL:")
        # self.archive_url_textedit = QLineEdit("http://lcls-archapp.slac.stanford.edu/")
        # self.archive_url_textedit.setFixedWidth(250)
        # self.archive_url_textedit.setFixedHeight(25)

        self.search_label = QLabel("Pattern:")
        self.search_box = QLineEdit()
        self.search_button = QPushButton("Search")
        self.search_button.setDefault(True)
        self.search_button.clicked.connect(self.request_archiver_info)

        self.loading_label = QLabel("Loading...")
        self.loading_label.hide()

        self.results_table_model = ArchiveResultsTableModel()
        self.results_view = QTableView(self)
        self.results_view.setModel(self.results_table_model)
        self.results_view.setProperty("showDropIndicator", False)
        self.results_view.setDragDropOverwriteMode(False)
        self.results_view.setDragEnabled(True)
        self.results_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.results_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.results_view.setDropIndicatorShown(True)
        self.results_view.setCornerButtonEnabled(False)
        self.results_view.setSortingEnabled(True)
        self.results_view.verticalHeader().setVisible(False)
        self.results_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_view.startDrag = self.startDragAction

        self.archive_url_layout = QHBoxLayout()
        # self.archive_url_layout.addWidget(self.archive_title_label)
        # self.archive_url_layout.addWidget(self.archive_url_textedit)
        self.layout.addLayout(self.archive_url_layout)
        self.search_layout = QHBoxLayout()
        self.search_layout.addWidget(self.search_label)
        self.search_layout.addWidget(self.search_box)
        self.search_layout.addWidget(self.search_button)
        self.layout.addLayout(self.search_layout)
        self.layout.addWidget(self.loading_label)
        self.layout.addWidget(self.results_view)
        # self.insert_button = QPushButton("Add PVs")
        # self.insert_button.clicked.connect(
        #    lambda: self.append_PVs_requested.emit(self.selectedPVs())
        # )
        self.results_view.doubleClicked.connect(
            lambda: self.append_PVs_requested.emit(self.selectedPVs())
        )
        # self.layout.addWidget(self.insert_button)
        self.setLayout(self.layout)

    def selectedPVs(self) -> str:
        """Figure out based on which indexes were selected, the list of PVs (by string name)
        The user was hoping to insert into the table. Concatenate them into string form i.e.
        <pv1>, <pv2>, <pv3>"""
        indices = self.results_view.selectedIndexes()
        pv_list = ""
        for index in indices:
            pv_name = self.results_table_model.results_list[index.row()]
            pv_list += pv_name + ", "
        return pv_list[:-2]

    def startDragAction(self, supported_actions) -> None:
        """
        The method to be called when a user initiates a drag action for one of the results in the table. The current
        reason for this functionality is the ability to drag a PV name onto a plot to automatically start drawing
        data for that PV
        """
        drag = QDrag(self)
        mime_data = QMimeData()
        mime_data.setText(self.selectedPVs())
        drag.setMimeData(mime_data)
        drag.exec_()

    def keyPressEvent(self, e: QKeyEvent) -> None:
        """Special key press tracker, just so that if enter or return is pressed the formula dialog attempts to submit the formula"""
        if e.key() == Qt.Key_Return or e.key() == Qt.Key_Enter:
            self.request_archiver_info()
        return super().keyPressEvent(e)

    def request_archiver_info(self) -> None:
        """ """
        search_text = self.search_box.text()
        search_text = search_text.replace("?", ".")
        request = self.env.search(search_text)

        if request is None:
            request = ""

        self.network_manager.get(request)
        self.loading_label.show()

    def populate_results_list(self, reply: QNetworkReply) -> None:
        """Slot called when the archiver appliance returns search results. Will populate the table with the results"""
        self.loading_label.hide()
        if reply.error() == QNetworkReply.NoError:
            self.results_table_model.clear()
            bytes_str = reply.readAll()
            pv_list = str(bytes_str, "utf-8").split()
            self.results_table_model.replace_rows(pv_list)
        else:
            logger.error(f"Could not retrieve archiver results due to: {reply.error()}")
        reply.deleteLater()
