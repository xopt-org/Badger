from importlib import resources
from PyQt5.QtWidgets import QWidget, QAbstractSpinBox, QPushButton
from PyQt5.QtCore import Qt, QObject, QEvent, QSize
from PyQt5.QtGui import QIcon


def preventAnnoyingSpinboxScrollBehaviour(
        self, control: QAbstractSpinBox) -> None:
    control.setFocusPolicy(Qt.StrongFocus)
    control.installEventFilter(self.MouseWheelWidgetAdjustmentGuard(control))


class MouseWheelWidgetAdjustmentGuard(QObject):
    def __init__(self, parent: QObject):
        super().__init__(parent)

    def eventFilter(self, o: QObject, e: QEvent) -> bool:
        widget: QWidget = o
        if e.type() == QEvent.Wheel and not widget.hasFocus():
            e.ignore()
            return True
        return super().eventFilter(o, e)


def create_button(icon_file, tooltip,
                  stylesheet=None, size=(32, 32), icon_size=None):
    icon_ref = resources.files(__package__) / f'./images/{icon_file}'
    with resources.as_file(icon_ref) as icon_path:
        icon = QIcon(str(icon_path))

    btn = QPushButton()
    if size:
        btn.setFixedSize(*size)
    btn.setIcon(icon)
    btn.setToolTip(tooltip)
    if icon_size:
        btn.setIconSize(QSize(*icon_size))

    if stylesheet is not None:
        btn.setStyleSheet(stylesheet)

    return btn
