# PyQt Functionality Snippet by Apocalyptech
# "Licensed" in the Public Domain under CC0 1.0 Universal (CC0 1.0)
# Public Domain Dedication.  Use it however you like!
#
# https://creativecommons.org/publicdomain/zero/1.0/
# https://creativecommons.org/publicdomain/zero/1.0/legalcode

from PyQt5 import QtWidgets, QtGui


class MyModel(QtGui.QStandardItemModel):
    def dropMimeData(self, data, action, row, col, parent):
        """
        Always move the entire row, and don't allow column "shifting"
        """
        return super().dropMimeData(data, action, row, 0, parent)


class MyStyle(QtWidgets.QProxyStyle):
    def drawPrimitive(self, element, option, painter, widget=None):
        """
        Draw a line across the entire row rather than just the column
        we're hovering over.  This may not always work depending on global
        style - for instance I think it won't work on OSX.
        """
        if element == self.PE_IndicatorItemViewItemDrop and not option.rect.isNull():
            option_new = QtWidgets.QStyleOption(option)
            option_new.rect.setLeft(0)
            if widget:
                option_new.rect.setRight(widget.width())
            option = option_new
        super().drawPrimitive(element, option, painter, widget)


class MyTableView(QtWidgets.QTableView):
    def __init__(self, parent):
        super().__init__(parent)
        self.verticalHeader().hide()
        self.horizontalHeader().hide()
        self.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.Stretch)
        self.setSelectionBehavior(self.SelectRows)
        self.setSelectionMode(self.SingleSelection)
        self.setShowGrid(False)
        self.setDragDropMode(self.InternalMove)
        self.setDragDropOverwriteMode(False)

        # Set our custom style - this draws the drop indicator across the whole row
        self.setStyle(MyStyle())

        # Set our custom model - this prevents row "shifting"
        self.model = MyModel()
        self.setModel(self.model)

        for idx, data in enumerate(["foo", "bar", "baz"]):
            item_1 = QtGui.QStandardItem("Item {}".format(idx))
            item_1.setEditable(False)
            item_1.setDropEnabled(False)

            item_2 = QtGui.QStandardItem(data)
            item_2.setEditable(False)
            item_2.setDropEnabled(False)

            self.model.appendRow([item_1, item_2])
