from PyQt5.QtWidgets import QHBoxLayout, QPushButton, QWidget
from PyQt5.QtWidgets import QStyledItemDelegate
from badger.gui.default.utils import NoHoverFocusComboBox


def state_item(options, remove_item, name=None):
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
    except:
        idx = 0
    cb_sta.setCurrentIndex(idx)

    widget.btn_del = btn_del = QPushButton("Remove")
    btn_del.setFixedSize(72, 24)
    btn_del.hide()

    hbox.addWidget(cb_sta, 1)
    hbox.addWidget(btn_del)

    btn_del.clicked.connect(remove_item)

    def show_button(event):
        btn_del.show()

    def hide_button(event):
        btn_del.hide()

    widget.enterEvent = show_button
    widget.leaveEvent = hide_button

    return widget
