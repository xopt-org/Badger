from PyQt5.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QWidget,
    QDoubleSpinBox,
    QAbstractSpinBox,
)
from PyQt5.QtWidgets import QComboBox, QCheckBox, QStyledItemDelegate
from PyQt5.QtCore import Qt
from badger.gui.default.utils import (
    MouseWheelWidgetAdjustmentGuard,
    NoHoverFocusComboBox,
)


def constraint_item(
    options, remove_item, name=None, relation=0, threshold=0, critical=False, decimals=4
):
    # relation: 0 for >, 1 for <, 2 for =
    widget = QWidget()
    hbox = QHBoxLayout(widget)
    hbox.setContentsMargins(2, 2, 2, 2)
    # hbox.setSpacing(0)
    widget.cb_obs = cb_obs = NoHoverFocusComboBox()
    cb_obs.setFixedWidth(200)
    cb_obs.setItemDelegate(QStyledItemDelegate())
    cb_obs.addItems(options)
    try:
        idx = options.index(name)
    except:
        idx = 0
    cb_obs.setCurrentIndex(idx)

    widget.cb_rel = cb_rel = QComboBox()
    cb_rel.setItemDelegate(QStyledItemDelegate())
    cb_rel.addItems([">", "<", "="])
    cb_rel.setFixedWidth(64)
    cb_rel.setCurrentIndex(relation)

    widget.sb = sb = QDoubleSpinBox()
    sb.setDecimals(decimals)
    sb.setFocusPolicy(Qt.StrongFocus)
    sb.installEventFilter(MouseWheelWidgetAdjustmentGuard(sb))
    default_value = threshold
    lb = default_value - 1e3
    ub = default_value + 1e3
    sb.setRange(lb, ub)
    sb.setStepType(QAbstractSpinBox.AdaptiveDecimalStepType)
    sb.setValue(default_value)

    widget.check_crit = check_crit = QCheckBox("Critical")
    check_crit.setChecked(critical)

    widget.btn_del = btn_del = QPushButton("Remove")
    btn_del.setFixedSize(72, 24)
    btn_del.hide()

    hbox.addWidget(check_crit)
    hbox.addWidget(cb_obs)
    hbox.addWidget(cb_rel)
    hbox.addWidget(sb, 1)
    hbox.addWidget(btn_del)

    btn_del.clicked.connect(remove_item)

    def show_button(event):
        btn_del.show()

    def hide_button(event):
        btn_del.hide()

    widget.enterEvent = show_button
    widget.leaveEvent = hide_button

    return widget
