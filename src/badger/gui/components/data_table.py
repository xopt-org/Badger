"""Helpers for creating and populating QTableWidgets that display
optimization data (variables, objectives, constraints) with clipboard
copy and alternating-row styling."""

import logging
from typing import Any

from gest_api.vocs import VOCS
from pandas import DataFrame
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QApplication, QTableWidget, QTableWidgetItem

logger = logging.getLogger(__name__)

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

stylesheet_data = """
    QTableWidget
    {
        margin: 0px 8px 8px 8px;
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

    def keyPressEvent(self, event: QKeyEvent | None) -> None:
        super().keyPressEvent(event)
        if (
            event is not None
            and event.key() == Qt.Key.Key_C
            and (event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        ):
            copied_cells = sorted(
                self.selectedIndexes(), key=lambda idx: (idx.row(), idx.column())
            )

            copy_text = ""
            max_column = copied_cells[-1].column()
            for c in copied_cells:
                item = self.item(c.row(), c.column())
                if item is not None:
                    copy_text += item.text()
                if c.column() == max_column:
                    copy_text += "\n"
                else:
                    copy_text += "\t"

            clipboard = QApplication.clipboard()
            if clipboard is not None:
                clipboard.setText(copy_text)

    def set_uneditable(self) -> None:
        self.setEditTriggers(QTableWidget.NoEditTriggers)

    def set_editable(self) -> None:
        self.setEditTriggers(QTableWidget.DoubleClicked)


def format_value(v: Any) -> str:
    try:
        f = f"{v:.6g}"
    except (ValueError, TypeError):
        f = str(v)
    return f


def resize_columns_to_content_or_default(table: QTableWidget) -> None:
    """Resize columns to the maximum of default width and content width."""
    hheader = table.horizontalHeader()
    if hheader is None:
        logger.warning("Horizontal header is None, cannot resize columns.")
        return
    default_width = hheader.defaultSectionSize()
    table.resizeColumnsToContents()
    for col in range(table.columnCount()):
        current_width = table.columnWidth(col)
        table.setColumnWidth(col, max(default_width, current_width))


def update_table(
    table: TableWithCopy,
    data: DataFrame | None = None,
    vocs: VOCS | None = None,
    info: bool = False,
) -> TableWithCopy:
    table.setRowCount(0)
    hheader = table.horizontalHeader()
    if hheader is None:
        logger.warning("Horizontal header is None, cannot hide it.")
    else:
        hheader.setVisible(False)

    if data is None:
        return table

    if vocs is None:
        raise ValueError("vocs must be provided to update the table")

    if info:
        columns = data.columns
    else:
        columns = vocs.output_names + vocs.variable_names

    _data = data[columns]

    m, n = _data.shape
    table.setRowCount(m)
    table.setColumnCount(n)
    for i in range(m):
        for j in range(n):
            v = _data.iloc[i, j]
            if isinstance(v, str):
                table.setItem(i, j, QTableWidgetItem(v))
            else:
                table.setItem(i, j, QTableWidgetItem(format_value(v)))
    table.setHorizontalHeaderLabels(list(_data.columns))
    table.setVerticalHeaderLabels(
        list(map(str, _data.index))
    )  # row index starts from 0
    hheader = table.horizontalHeader()
    if hheader is None:
        logger.warning("Horizontal header is None, cannot show it.")
    else:
        hheader.setVisible(True)
    resize_columns_to_content_or_default(table)

    return table


def reset_table(table: TableWithCopy, header: list[str]) -> TableWithCopy:
    table.setRowCount(0)
    # Need to set col num or the old col num will be used for new data,
    # resulting in potential incomplete table
    table.setColumnCount(len(header))
    hheader = table.horizontalHeader()
    if hheader is None:
        logger.warning("Horizontal header is None, cannot hide it.")
    else:
        hheader.setVisible(False)
    table.setHorizontalHeaderLabels(header)
    hheader = table.horizontalHeader()
    if hheader is None:
        logger.warning("Horizontal header is None, cannot show it.")
    else:
        hheader.setVisible(True)

    return table


def add_row(table: TableWithCopy, row: list[float | str]) -> TableWithCopy:
    r = table.rowCount()
    table.insertRow(r)
    for i, v in enumerate(row):
        table.setItem(r, i, QTableWidgetItem(format_value(v)))
    table.setVerticalHeaderItem(r, QTableWidgetItem(str(r)))

    return table


def data_table(data: DataFrame | None = None) -> TableWithCopy:
    table = TableWithCopy()
    table.setAlternatingRowColors(True)
    table.setStyleSheet(stylesheet_data)
    # table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
    return update_table(table, data)


def init_data_table(variable_names: list[str] | None = None) -> TableWithCopy:
    table = TableWithCopy()
    table.setAlternatingRowColors(True)
    table.setStyleSheet(stylesheet)
    # table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

    table.setRowCount(10)
    if variable_names is None:
        return table

    table.setColumnCount(len(variable_names))
    hheader = table.horizontalHeader()
    if hheader is None:
        logger.warning("Horizontal header is None, cannot hide it.")
    else:
        hheader.setVisible(False)
    table.setHorizontalHeaderLabels(variable_names)
    hheader = table.horizontalHeader()
    if hheader is None:
        logger.warning("Horizontal header is None, cannot show it.")
    else:
        hheader.setVisible(True)
    resize_columns_to_content_or_default(table)

    return table


def get_horizontal_header_as_list(table: TableWithCopy) -> list[str]:
    header = table.horizontalHeader()
    if header is None:
        logger.warning("Horizontal header is None, cannot read labels.")
        return []
    model = header.model()
    if model is None:
        logger.warning("Header model is None, cannot read labels.")
        return []
    header_labels = [
        model.headerData(i, header.orientation()) for i in range(header.count())
    ]
    return header_labels


def get_table_content_as_dict(table: TableWithCopy) -> dict[str, list[str]]:
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


def update_init_data_table(table: TableWithCopy, variable_names: list[str]) -> None:
    current_init_data = get_table_content_as_dict(table)

    table.setColumnCount(len(variable_names))
    hheader = table.horizontalHeader()
    if hheader is None:
        logger.warning("Horizontal header is None, cannot hide it.")
    else:
        hheader.setVisible(False)
    table.setHorizontalHeaderLabels(variable_names)
    hheader = table.horizontalHeader()
    if hheader is None:
        logger.warning("Horizontal header is None, cannot show it.")
    else:
        hheader.setVisible(True)

    for col, name in enumerate(variable_names):
        if name in current_init_data:
            for row in range(table.rowCount()):
                table.setItem(row, col, QTableWidgetItem(current_init_data[name][row]))
        else:
            for row in range(table.rowCount()):
                table.setItem(row, col, QTableWidgetItem(""))


def set_init_data_table(table: TableWithCopy, data: DataFrame) -> None:
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
            table.setItem(
                row, col, QTableWidgetItem(format_value(data_dict[name][row]))
            )
