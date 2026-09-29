"""QTableView with drag-and-drop row reordering and a custom drop-indicator
line style."""

# PyQt Functionality Snippet by Apocalyptech
# "Licensed" in the Public Domain under CC0 1.0 Universal (CC0 1.0)
# Public Domain Dedication.  Use it however you like!
#
# https://creativecommons.org/publicdomain/zero/1.0/
# https://creativecommons.org/publicdomain/zero/1.0/legalcode

from PyQt5.QtCore import QMimeData, QModelIndex, Qt
from PyQt5.QtGui import QPainter, QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import (
    QHeaderView,
    QProxyStyle,
    QStyle,
    QStyleOption,
    QTableView,
    QWidget,
)


class MyModel(QStandardItemModel):
    def dropMimeData(
        self,
        data: QMimeData | None,
        action: Qt.DropAction,
        row: int,
        col: int,
        parent: QModelIndex,
    ) -> bool:
        """
        Always move the entire row, and don't allow column "shifting"
        """
        return super().dropMimeData(data, action, row, 0, parent)


class MyStyle(QProxyStyle):
    def drawPrimitive(
        self,
        element: QStyle.PrimitiveElement,
        option: QStyleOption | None,
        painter: QPainter | None,
        widget: QWidget | None = None,
    ) -> None:
        """
        Draw a line across the entire row rather than just the column
        we're hovering over.  This may not always work depending on global
        style - for instance I think it won't work on OSX.
        """
        if (
            element == QStyle.PrimitiveElement.PE_IndicatorItemViewItemDrop
            and option is not None
            and not option.rect.isNull()
        ):
            option_new = QStyleOption(option)
            option_new.rect.setLeft(0)
            if widget:
                option_new.rect.setRight(widget.width())
            option = option_new
        super().drawPrimitive(element, option, painter, widget)


class MyTableView(QTableView):
    def __init__(self, parent: QWidget | None) -> None:
        super().__init__(parent)
        vheader = self.verticalHeader()
        if vheader:
            vheader.hide()
        hheader = self.horizontalHeader()
        if hheader:
            hheader.hide()
            hheader.setSectionResizeMode(QHeaderView.Stretch)
        self.setSelectionBehavior(self.SelectRows)
        self.setSelectionMode(self.SingleSelection)
        self.setShowGrid(False)
        self.setDragDropMode(self.InternalMove)
        self.setDragDropOverwriteMode(False)

        # Set our custom style - this draws the drop indicator across the whole row
        self.setStyle(MyStyle())

        # Set our custom model - this prevents row "shifting"
        self._model = MyModel()
        self.setModel(self._model)

        for idx, data in enumerate(["foo", "bar", "baz"]):
            item_1 = QStandardItem(f"Item {idx}")
            item_1.setEditable(False)
            item_1.setDropEnabled(False)

            item_2 = QStandardItem(data)
            item_2.setEditable(False)
            item_2.setDropEnabled(False)

            self._model.appendRow([item_1, item_2])
