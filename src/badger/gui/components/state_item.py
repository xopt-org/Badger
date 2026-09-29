"""Creates a single observable-state row: a combo box for the observable
name and a remove button."""

from collections.abc import Callable

from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QHBoxLayout, QPushButton, QStyledItemDelegate, QWidget

from badger.gui.utils import NoHoverFocusComboBox


def state_item(options: list[str], remove_item: Callable, name: str = "") -> QWidget:
    widget = QWidget()
    hbox = QHBoxLayout(widget)
    hbox.setContentsMargins(2, 2, 2, 2)
    # hbox.setSpacing(0)
    widget.cb_sta = cb_sta = NoHoverFocusComboBox()
    # cb_sta.setFixedWidth(200)
    cb_sta.setItemDelegate(QStyledItemDelegate())
    cb_sta.addItems(options)
    try:
        idx = options.index(name)
    except ValueError:
        idx = 0
    cb_sta.setCurrentIndex(idx)

    widget.btn_del = btn_del = QPushButton("Remove")
    btn_del.setFixedSize(72, 24)
    btn_del.hide()

    hbox.addWidget(cb_sta, 1)
    hbox.addWidget(btn_del)

    btn_del.clicked.connect(remove_item)

    def show_button(event: QEvent | None) -> None:
        btn_del.show()

    def hide_button(event: QEvent | None) -> None:
        btn_del.hide()

    widget.enterEvent = show_button
    widget.leaveEvent = hide_button

    return widget
