"""Creates a single constraint row widget: observable selector, relation
combo (>, <, =), threshold spinbox, criticality checkbox, and remove button."""

from collections.abc import Callable

from PyQt5 import QtCore
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QPushButton,
    QStyledItemDelegate,
    QWidget,
)

from badger.gui.utils import (
    MouseWheelWidgetAdjustmentGuard,
    NoHoverFocusComboBox,
)


class ConstraintItem(QWidget):
    """A single constraint row that exposes its input widgets as attributes."""

    cb_obs: NoHoverFocusComboBox
    cb_rel: QComboBox
    sb: QDoubleSpinBox
    check_crit: QCheckBox
    btn_del: QPushButton

    def enterEvent(self, a0: QtCore.QEvent | None) -> None:
        self.btn_del.show()

    def leaveEvent(self, a0: QtCore.QEvent | None) -> None:
        self.btn_del.hide()


def constraint_item(
    options: list[str],
    remove_item: Callable[[], None],
    name: str = "",
    relation: int = 0,
    threshold: float = 0,
    critical: bool = False,
    decimals: int = 4,
) -> ConstraintItem:
    # relation: 0 for >, 1 for <, 2 for =
    widget = ConstraintItem()
    hbox = QHBoxLayout(widget)
    hbox.setContentsMargins(2, 2, 2, 2)
    # hbox.setSpacing(0)
    widget.cb_obs = cb_obs = NoHoverFocusComboBox()
    cb_obs.setFixedWidth(200)
    cb_obs.setItemDelegate(QStyledItemDelegate())
    cb_obs.addItems(options)
    try:
        idx = options.index(name)
    except ValueError:
        idx = 0
    cb_obs.setCurrentIndex(idx)

    widget.cb_rel = cb_rel = QComboBox()
    cb_rel.setItemDelegate(QStyledItemDelegate())
    cb_rel.addItems([">", "<", "="])
    cb_rel.setFixedWidth(64)
    cb_rel.setCurrentIndex(relation)

    widget.sb = sb = QDoubleSpinBox()
    sb.setDecimals(decimals)
    sb.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
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

    return widget
