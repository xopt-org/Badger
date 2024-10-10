from pandas import DataFrame
from PyQt5.QtWidgets import QApplication, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt


stylesheet = """
    QTableWidget
    {
        alternate-background-color: #262E38;
    }
    QTableWidget::item::selected
    {
        background-color: #B3E5FC;
        color: #000000;
    }
"""


# https://stackoverflow.com/questions/60715462/how-to-copy-and-paste-multiple-cells-in-qtablewidget-in-pyqt5
class TableWithCopy(QTableWidget):
    """
    this class extends QTableWidget
    * supports copying multiple cell's text onto the clipboard
    * formatted specifically to work with multiple-cell paste into programs
      like google sheets, excel, or numbers
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def keyPressEvent(self, event):
        super().keyPressEvent(event)
        if event.key() == Qt.Key.Key_C and (
            event.modifiers() & Qt.KeyboardModifier.ControlModifier
        ):
            copied_cells = sorted(self.selectedIndexes())

            copy_text = ""
            max_column = copied_cells[-1].column()
            for c in copied_cells:
                copy_text += self.item(c.row(), c.column()).text()
                if c.column() == max_column:
                    copy_text += "\n"
                else:
                    copy_text += "\t"

            QApplication.clipboard().setText(copy_text)

    def set_uneditable(self):
        self.setEditTriggers(QTableWidget.NoEditTriggers)

    def set_editable(self):
        self.setEditTriggers(QTableWidget.DoubleClicked)


def update_table(table, data=None):
    table.setRowCount(0)
    table.horizontalHeader().setVisible(False)

    if data is None:
        return table

    _data = data.drop(columns=["timestamp", "xopt_error", "xopt_runtime"])

    m, n = _data.shape
    table.setRowCount(m)
    table.setColumnCount(n)
    for i in range(m):
        for j in range(n):
            v = _data.iloc[i, j]
            table.setItem(i, j, QTableWidgetItem(f"{v:.4g}"))
    table.setHorizontalHeaderLabels(list(_data.columns))
    table.setVerticalHeaderLabels(
        list(map(str, _data.index))
    )  # row index starts from 0
    table.horizontalHeader().setVisible(True)

    return table


def reset_table(table, header):
    table.setRowCount(0)
    # Need to set col num or the old col num will be used for new data,
    # resulting in potential incomplete table
    table.setColumnCount(len(header))
    table.horizontalHeader().setVisible(False)
    table.setHorizontalHeaderLabels(header)
    table.horizontalHeader().setVisible(True)

    return table


def add_row(table, row):
    r = table.rowCount()
    table.insertRow(r)
    for i, v in enumerate(row):
        table.setItem(r, i, QTableWidgetItem(f"{v:.4g}"))
    table.setVerticalHeaderItem(r, QTableWidgetItem(str(r)))

    return table


def data_table(data=None):
    table = TableWithCopy()
    table.setAlternatingRowColors(True)
    table.setStyleSheet(stylesheet)
    # table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    return update_table(table, data)


def init_data_table(variable_names=None):
    table = TableWithCopy()
    table.setAlternatingRowColors(True)
    table.setStyleSheet(stylesheet)
    # table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    table.setRowCount(10)
    if variable_names is None:
        return table

    table.setColumnCount(len(variable_names))
    table.horizontalHeader().setVisible(False)
    table.setHorizontalHeaderLabels(variable_names)
    table.horizontalHeader().setVisible(True)

    return table


def get_horizontal_header_as_list(table):
    header = table.horizontalHeader()
    header_labels = [
        header.model().headerData(i, header.orientation())
        for i in range(header.count())
    ]
    return header_labels


def get_table_content_as_dict(table):
    table_content = {}
    header_labels = get_horizontal_header_as_list(table)

    for col in range(table.columnCount()):
        column_name = header_labels[col]
        column_values = []

        for row in range(table.rowCount()):
            item = table.item(row, col)
            if item is not None:
                column_values.append(item.text())
            else:
                column_values.append("")

        table_content[column_name] = column_values

    return table_content


def update_init_data_table(table, variable_names):
    current_init_data = get_table_content_as_dict(table)

    table.setColumnCount(len(variable_names))
    table.horizontalHeader().setVisible(False)
    table.setHorizontalHeaderLabels(variable_names)
    table.horizontalHeader().setVisible(True)

    for col, name in enumerate(variable_names):
        if name in current_init_data:
            for row in range(table.rowCount()):
                table.setItem(row, col, QTableWidgetItem(current_init_data[name][row]))
        else:
            for row in range(table.rowCount()):
                table.setItem(row, col, QTableWidgetItem(""))


def set_init_data_table(table, data: DataFrame):
    variable_names = get_horizontal_header_as_list(table)
    try:
        data_dict = data.to_dict("list")
    except AttributeError:
        data_dict = None

    # Clear the table
    for col, name in enumerate(variable_names):
        for row in range(table.rowCount()):
            table.setItem(row, col, QTableWidgetItem(""))

    if data_dict is None:
        return

    # Fill the table
    for col, name in enumerate(variable_names):
        for row in range(len(data_dict[name])):
            table.setItem(row, col, QTableWidgetItem(f"{data_dict[name][row]:.4g}"))
