from typing import Dict, Any
from PyQt5.QtGui import QKeyEvent, QPainter
from PyQt5.QtCore import (pyqtSlot, QModelIndex, QObject, Qt, pyqtSignal, QAbstractItemModel, QAbstractTableModel, QVariant, QEvent)
from PyQt5.QtWidgets import (QHeaderView, QMenu, QAction, QTableView, QDialog,
                            QVBoxLayout, QGridLayout, QLineEdit, QPushButton, QAbstractItemView, QTableWidget, QStyleOptionViewItem, QWidget, QStyledItemDelegate, QLabel, QHBoxLayout)
from badger.gui.default.components.archive_search import ArchiveSearchWidget
from abc import abstractmethod


class EditorDelegate(QStyledItemDelegate):
    """Abstract Base Class for QStyledItemDelegates that display a persistent
    editor. When inheriting from this class, make sure to override abstract
    methods: createEditor, setEditorData, setModelData

    Parameters
    ----------
    parent : QTableView
        The QTableView associated with the delegate. Used for opening
        persistent editors.
    """
    def __init__(self, parent: QTableView) -> None:
        super().__init__(parent)
        self.editor_list = []
        model = self.parent().model()
        model.modelAboutToBeReset.connect(self.reset_editors)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex) -> None:
        """Create a new persistent editor on the Table View at the given index.

        Parameters
        ----------
        painter : QtGui.QPainter
            The Qt Painter used to display the delegate's editors
        option : QtWidgets.QStyleOptionViewItem
            The style option used to render the item
        index : QModelIndex
            The index to display the editor on
        """
        if index.row() == len(self.editor_list):
            self.parent().openPersistentEditor(index)
        return super().paint(painter, option, index)

    @abstractmethod
    def createEditor(self, parent: QWidget, option: QStyleOptionViewItem, index: QModelIndex) -> QWidget:
        """Editor creator function to be overridden by subclasses.

        Parameters
        ----------
        parent : QWidget
            The parent widget intended to be used as the parent of the new editor
        option : QStyleOptionViewItem
            The item options used in creating the editor
        index : QModelIndex
            The index to display the editor on

        Returns
        -------
        QWidget
            The QWidget editor for the specified index
        """
        return super().createEditor(parent, option, index)

    def destroyEditor(self, editor: QWidget, index: QModelIndex) -> None:
        """Close the persistent editor for a defined index.

        Parameters
        ----------
        editor : QWidget
            The editor to be destroyed
        index : QModelIndex
            The index of the editor to be destroyed
        """
        if index.row() < len(self.editor_list):
            del self.editor_list[index.row()]
            editor.deleteLater()
            self.parent().closePersistentEditor(index)
            return
        return super().destroyEditor(editor, index)

    @abstractmethod
    def setEditorData(self, editor: QWidget, index: QModelIndex) -> None:
        """Abstract method to be overridden by subclasses. Sets the
        delegate's editor to match the table model's data.

        Parameters
        ----------
        editor : QWidget
            The editor which will need to be set. Changes type based on
            how the subclass is implemented.
        index : QModelIndex
            The index of the editor to be changed.
        """
        return super().setEditorData(editor, index)

    @abstractmethod
    def setModelData(self, editor: QWidget, model: QAbstractItemModel, index: QModelIndex) -> None:
        """Abstract method to be overridden by subclasses. Sets the
        table's model data to match the delegate's editor.

        Parameters
        ----------
        editor : QWidget
            The editor containing the data to be saved in the model. Changes
            type based on how the subclass is implemented.
        model : QAbstractItemModel
            The model which will need to be set.
        index : QModelIndex
            The index of the editor to be changed.
        """
        return super().setModelData(editor, model, index)

    @pyqtSlot()
    def reset_editors(self) -> None:
        """Slot called when the delegate's model will be reset. Closes all
        persistent editors in the delegate.
        """
        for editor in self.editor_list:
            editor_pos = editor.pos()
            index = self.parent().indexAt(editor_pos)

            editor.deleteLater()
            self.parent().closePersistentEditor(index)
        self.editor_list = []
                           

class InsertPVDelegate(QStyledItemDelegate):
    """InsertPVDelegate displays a persistent QPushButton widget that allows the user to insert the PV."""

    button_clicked = pyqtSignal(str)

    def __init__(self, parent: QTableView):
        super().__init__(parent)
        self.model = self.parent().model()

    def paint(self, painter, option, index):
        if not index.isValid():
            return
        if index.row() >= index.model().rowCount() - 1:
            # Do not display button in the empty row
            return

        # Draw a push buttonwire:COL1:360:SPEED_OK_FLT_CALC
        button = QPushButton("Insert")
        button.setStyleSheet("QPushButton { margin: 2px; }")
        button.resize(option.rect.size())
        # Render the button onto the painter
        painter.save()
        painter.translate(option.rect.topLeft())
        button.render(painter)
        painter.restore()

    def editorEvent(self, event, model, option, index):
        if not index.isValid():
            return False
        if index.row() >= model.rowCount() - 1:
            # Do not handle events in the empty row
            return False
        if event.type() == QEvent.MouseButtonRelease:
            if option.rect.contains(event.pos()):
                # Handle the button click
                row_name = self.model._row_names[index.row()]
                self.button_clicked.emit("{" + row_name + "}")
                return True
        return False

    
class PVContextMenu(QMenu):
    # TODO: Change this QMenu so functions that change data stay in table object
    #   - Move functions to table widget
    #   - Init parameters: dict("ACTION_NAME": function)
    #   - Init: Loop through dict values:
    #       - Create action w/ name
    #       - action.triggered.connect(function)
    #       - self.addAction(action)

    # data_changed_signal = Signal(int)

    # TODO: Archived PVs are no longer draggable from the search tool. Find out why

    def __init__(self, parent: QObject = None) -> None:
        super().__init__(parent)
        self._selected_index = None
        self.archive_search = ArchiveSearchWidget()
        self._formula_dialog = FormulaDialog(self)

        # Add "SEARCH PV" option
        search_pv_action = QAction("SEARCH PV", self)
        search_pv_action.triggered.connect(self.archive_search.show)
        self.addAction(search_pv_action)

        # Add "FORMULA" option
        formula_action = QAction("FORMULA", self)
        #formula_action.triggered.connect(self._formula_dialog.exec_)
        self.addAction(formula_action)

    @property
    def selected_index(self) -> QModelIndex:
        """Get the table's selected index."""
        return self._selected_index

    @selected_index.setter
    def selected_index(self, ind: QModelIndex) -> None:
        """Set the table's selected index."""
        self._selected_index = ind


class FormulaDialog(QDialog):
    """Formula Dialog - when a user right clicks on a row in the list of curves, they have the option to input a formula
    They could opt to type it instead, but this opens a box that is a nicer UI for inputting a formula."""
    def __init__(self, parent: QObject) -> None:
        super().__init__(parent)
        self.setWindowTitle("Formula Input")

        # Create the layout for the dialog
        layout = QVBoxLayout(self)
        # Create the QLineEdit for formula input
        self.field = QLineEdit(self)
        self.name_field = QLineEdit(self)
        self.name = QLabel("Name:")
        #self.curveModel = self.parent().parent().curves_model
        self.pv_list = QTableView(self)
        
        self.model = PVTableModel()
        self.pv_list.setModel(self.model)

        #We're going to copy the list of PVs from the curve model. We're also not going to allow the user to make edits to the list of PVs
        #self.pv_list.setModel(self.curveModel)
        #self.pv_list.setEditTriggers(QAbstractItemView.EditTriggers(0))
        self.pv_list.setMaximumWidth(1000)
        self.pv_list.setMaximumHeight(1000)
        header = self.pv_list.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        #for i in range(1, self.curveModel.columnCount() - 1):
            # Hide all columns that arent useful, but keep one left over to add a button to
            # self.pv_list.setColumnHidden(i, True)

        insertButton = InsertPVDelegate(self.pv_list)
        insertButton.button_clicked.connect(self.field.insert)
        self.pv_list.setItemDelegateForColumn(1, insertButton)

        #delete_delegate = DeleteButtonDelegate(self.pv_list)
        #self.pv_list.setItemDelegateForColumn(2, delete_delegate)
        
        self.pv_list.setAcceptDrops(True)
        self.pv_list.setDragDropMode(QAbstractItemView.DragDrop)
        self.pv_list.viewport().setAcceptDrops(True)

        name_layout = QHBoxLayout()
        name_layout.addWidget(self.name)
        name_layout.addWidget(self.name_field)
        
        layout.addWidget(self.pv_list)
        layout.addLayout(name_layout)
        layout.addWidget(self.field)

        # self.index = self.parent().selected_index

        # Define the list of calculator buttons.
        # It's a bunch of preset buttons, but users can type other functions under math.
        buttons = ["7",       "8",     "9",      "+",     "(",      ")",
                   "4",       "5",     "6",      "-",    "^2", "sqrt()",
                   "1",       "2",     "3",      "*",   "^-1",  "ln()",
                   "0",       "e",    "pi",      "/", "sin()", "asin()",
                   ".",   "abs()", "min()",      "^", "cos()", "acos()",
                   "PV",  "Clear", "max()", "mean()", "tan()", "atan()"]

        # Create the calculator buttons and connect them to the input field
        grid_layout = QGridLayout()
        for i, button_text in enumerate(buttons):
            button = QPushButton(button_text, self)
            row = i // 6
            col = i % 6
            grid_layout.addWidget(button, row, col)
            # Connect the button clicked signal to the appropriate action
            # PV currently does nothing, this is a remnant
            # From when we would have the pv_list open in a new window
            if button_text == "PV":
                self.PVButton = button
                self.PVButton.setCheckable(True)
                self.PVButton.clicked.connect(self.archiveSearchMenu)
            elif button_text == "Clear":
                button.clicked.connect(lambda _: self.field.clear())
            else:
                button.clicked.connect(lambda _, text=button_text: self.field.insert(text))
        layout.addLayout(grid_layout)

        # Add an "OK" button to accept the formula and close the dialog
        ok_button = QPushButton("OK", self)
        ok_button.clicked.connect(self.saveFormula)
        layout.addWidget(ok_button)
        self.showPVList()
        self.pv_list.show()

    def keyPressEvent(self, e: QKeyEvent) -> None:
        # Special key press tracker, just so that if enter or return is pressed the formula dialog attempts to submit the formula
        if e.key() == Qt.Key_Return or e.key() == Qt.Key_Enter:
            self.accept_formula()
        return super().keyPressEvent(e)

    @pyqtSlot()
    def archiveSearchMenu(self):
        self.archive_search = ArchiveSearchWidget()
        self.archive_search.show()

    @pyqtSlot()
    def showPVList(self):
        show = self.PVButton.isChecked()
        if show:
            self.pv_list.show()
        else:
            self.pv_list.hide()

    '''
    def exec_(self):
        """ When the formula dialog is opened (every time) we need to
            update it with the latest information on the curve model and
            also populate the text bofx with the pre-existing formula (if it already was there)"""
        self.index = self.parent().selected_index
        self.pv_list.setRowHidden(len(self.curveModel._row_names) - 1, True)
        for i in range(self.curveModel.rowCount() - 1):
            self.pv_list.setRowHidden(i, False)
        index = self.curveModel.index(self.index.row(), 0)
        curve = self.curveModel._plot._curves[self.index.row()]
        if index.data() and isinstance(curve, FormulaCurveItem):
            self.field.setText(str(index.data()).strip("f://"))
        else:
            self.field.setText("")
        super().exec_()
    '''

    def accept_formula(self, **kwargs: Dict[str, Any]) -> None:
        # Retrieve the formula and PV name and perform desired actions
        # We take in the formula (prepend the formula tag) and attempt to create a curve. Iff it passes, we close the window
        formula = "f://" + self.field.text()
        # pv_name = self.pv_name_input.text()
        # passed = self.curveModel.replaceToFormula(index = self.curveModel.index(self.parent().selected_index.row(), 0), formula = formula)
        # if passed:
            # self.field.setText("")
            # self.accept()
    
    @pyqtSlot()
    def saveFormula(self):
        data_dict = self.model.getData()

        print(self.name_field.text(), self.field.text(), data_dict)
        return (self.name_field.text(), self.field.text(), data_dict)

class PVTableModel(QAbstractTableModel):
    headerDataChanged = pyqtSignal(Qt.Orientation, int, int)

    def __init__(self, data=None) -> None:
        super(PVTableModel, self).__init__()
        self._column_names = ["Channel", "Add to Formula"]
        self._row_names = []

        if data is None:
            self._data = []
        else:
            self._data = data

        # Initialize row names
        for _ in range(len(self._data)):
            self._row_names.append(self.next_header())

    def rowCount(self, parent=None):
        if parent is not None and parent.isValid():
            return 0
        return len(self._data) + 1  # Account for the extra empty row

    def columnCount(self, parent=None):
        return len(self._column_names)

    def data(self, index, role=Qt.DisplayRole):
        if role in (Qt.DisplayRole, Qt.EditRole):
            row = index.row()
            col = index.column()
            if row < len(self._data):
                if col == 2:
                    return ""  # The delete button does not need data
                return self._data[row][col]
            else:
                if col == 2:
                    return ""  # No delete button in the empty row
                return ''  # Empty string for the extra row
        return QVariant()

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            row = index.row()
            col = index.column()
            if row == len(self._data):
                # User is editing the extra empty row
                self.beginInsertRows(QModelIndex(), row, row)
                self._data.append([''] * self.columnCount())
                new_header = self.next_header()
                self._row_names.append(new_header)
                self.endInsertRows()
                # Emit signal to update the row headers
                self.headerDataChanged.emit(Qt.Vertical, row, row)
            # Set the data
            self._data[row][col] = value
            self.dataChanged.emit(index, index)
            return True
        return False

    def headerData(self, section, orientation, role=Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if section < len(self._column_names):
                    return self._column_names[section]
            elif orientation == Qt.Vertical:
                if section < len(self._row_names):
                    return self._row_names[section]
                elif section == len(self._row_names):
                    # Return the next header without adding it to _row_names
                    return self.next_header()
        return QVariant()

    def next_header(self) -> str:
        if not self._row_names:
            return 'A'

        prev_header = self._row_names[-1]
        next_header = ""

        if prev_header == 'Z' * len(prev_header):
            return 'A' * (len(prev_header) + 1)

        inc = 1
        for i in range(len(prev_header) - 1, -1, -1):
            old_val = ord(prev_header[i]) - ord('A') + inc
            inc = old_val // 26
            new_val = chr((old_val % 26) + ord('A'))
            next_header = new_val + next_header

        if inc > 0 and i == 0:
            next_header = 'A' + next_header

        return next_header

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if index.column() == 0:
            flags |= Qt.ItemIsEditable | Qt.ItemIsDropEnabled  # First column is editable and droppable
        return flags

    def mimeTypes(self):
        return ['text/plain']

    def dropMimeData(self, data, action, row, column, parent):
        #print(f"dropMimeData called with action={action}, row={row}, column={column}, parent={parent}")
        
        if action == Qt.IgnoreAction:
            return False
        if not data.hasText():
            return False

        # Get the dropped text and split it by commas
        text = data.text().strip()
        #print(f"Dropped text: {text}")
        strings = text.split(',')  # Split by comma
        #print(f"Strings to insert: {strings}")

        # Determine the starting row and column
        if row == -1:
            index = parent
            row = index.row()
        if column == -1:
            column = 0  # Start from the first column if no specific column is provided

        # Ensure we do not exceed row limits
        if row >= len(self._data):
            #print(f"Row {row} exceeds current data length, adding new rows")
            self.beginInsertRows(QModelIndex(), row, row + len(strings) - 1)
            # Add enough empty rows to accommodate all strings
            for _ in range(len(strings)):
                self._data.append([''] * (self.columnCount() - 1))
                self._row_names.append(self.next_header())
            self.endInsertRows()

        # Insert strings into consecutive cells
        current_row = row
        for string in strings:
            string = string.strip()  # Remove any extra whitespace
            if current_row < len(self._data):
                # Set the string in the first column (or change if needed)
                self.setData(self.index(current_row, column), string, Qt.EditRole)
                current_row += 1
            else:
                break

        return True


    def supportedDropActions(self):
        return Qt.CopyAction | Qt.MoveAction

    def removeRow(self, row, parent=QModelIndex()):
        if 0 <= row < len(self._data):
            self.beginRemoveRows(parent, row, row)
            del self._data[row]
            del self._row_names[row]
            self.endRemoveRows()
            # Emit signal to update the row headers
            self.headerDataChanged.emit(Qt.Vertical, row, len(self._row_names))
            return True
        return False

    def getData(self):
        """Returns a dictionary where row letters are the keys and 'Channel' column data are the values."""
        data_dict = {}
        for row_index, row_name in enumerate(self._row_names):
            # Only include rows with non-empty 'Channel' column data
            channel_data = self._data[row_index][0].strip()  # First column is the 'Channel' column
            if channel_data:  # Only include rows with non-empty channel data
                data_dict[row_name] = channel_data
        return data_dict


class DeleteButtonDelegate(QStyledItemDelegate):
    """Delegate to display a delete button in the third column."""

    def __init__(self, parent=None):
        super(DeleteButtonDelegate, self).__init__(parent)
        self.parent = parent  # The view

    def createEditor(self, parent, option, index):
        # No editor needed, as we're using a button in the display
        return None

    def paint(self, painter, option, index):
        if not index.isValid():
            return
        if index.row() >= index.model().rowCount() - 1:
            # Do not display button in the empty row
            return

        # Draw a push button
        button = QPushButton("Delete")
        button.setStyleSheet("QPushButton { margin: 2px; }")
        button.resize(option.rect.size())
        pixmap = button.grab()
        painter.drawPixmap(option.rect, pixmap)

    def editorEvent(self, event, model, option, index):
        if not index.isValid():
            return False
        if index.row() >= model.rowCount() - 1:
            # Do not handle events in the empty row
            return False
        if event.type() == QEvent.MouseButtonRelease:
            if option.rect.contains(event.pos()):
                # Handle the button click
                model.removeRow(index.row())
                return True
        return False