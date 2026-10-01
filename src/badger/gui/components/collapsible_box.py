"""Animated expand/collapse container. Used in the routine editor to
group environment config, generator parameters, etc. without taking
up permanent screen space."""

import logging
from typing import cast

from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtGui import QResizeEvent
from PyQt5.QtWidgets import (
    QLayout,
    QScrollArea,
    QSizePolicy,
    QToolButton,
    QWidget,
)

logger = logging.getLogger(__name__)

stylesheet_toolbutton = """
QToolButton
{
    border: none;
}
"""


# https://stackoverflow.com/a/56293688
class ScrollArea(QScrollArea):
    resized = pyqtSignal()

    def resizeEvent(self, a0: QResizeEvent | None) -> None:
        self.resized.emit()
        return super().resizeEvent(a0)


# https://stackoverflow.com/a/52617714/4263605
class CollapsibleBox(QWidget):
    def __init__(
        self,
        parent: QWidget | None = None,
        title: str = "",
        duration: int = 100,
        tooltip: str = "",
    ):
        super().__init__(parent)

        self.title = title
        self.duration = duration

        from PyQt5.QtGui import QFont

        cool_font = QFont()
        cool_font.setWeight(QFont.DemiBold)
        cool_font.setPixelSize(13)

        self.toggle_button = QToolButton()
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)
        self.toggle_button.setFont(cool_font)
        self.toggle_button.setFixedHeight(28)
        self.toggle_button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.toggle_button.setStyleSheet(stylesheet_toolbutton)
        self.toggle_button.setToolButtonStyle(
            QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon
        )
        self.toggle_button.setIconSize(QtCore.QSize(11, 11))
        self.toggle_button.setArrowType(QtCore.Qt.ArrowType.RightArrow)
        self.toggle_button.setToolTip(tooltip)
        self.toggle_button.clicked.connect(self.start_animation)
        # self.toggle_button.setText(f'+ {title}')

        self.toggle_animation = QtCore.QParallelAnimationGroup(self)

        self.content_area = ScrollArea()
        self.content_area.setMaximumHeight(0)
        self.content_area.setMinimumHeight(0)
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.content_area.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.content_area.resized.connect(self.updateContentLayout)

        lay = QtWidgets.QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.toggle_button)
        lay.addWidget(self.content_area)

        self.toggle_animation.addAnimation(
            QtCore.QPropertyAnimation(self, b"minimumHeight")
        )
        self.toggle_animation.addAnimation(
            QtCore.QPropertyAnimation(self, b"maximumHeight")
        )
        self.toggle_animation.addAnimation(
            QtCore.QPropertyAnimation(self.content_area, b"maximumHeight")
        )

    @QtCore.pyqtSlot()
    def start_animation(self) -> None:
        checked = self.toggle_button.isChecked()
        arrow_type = (
            QtCore.Qt.ArrowType.DownArrow if checked else QtCore.Qt.ArrowType.RightArrow
        )
        self.toggle_button.setArrowType(arrow_type)
        # self.toggle_button.setText(f'- {self.title}' if not checked else f'+ {self.title}')
        direction = (
            QtCore.QAbstractAnimation.Direction.Forward
            if checked
            else QtCore.QAbstractAnimation.Direction.Backward
        )
        self.toggle_animation.setDirection(direction)
        self.toggle_animation.start()

    def expand(self) -> None:
        if not self.toggle_button.isChecked():
            self.toggle_button.click()

    def updateContentLayout(self) -> None:
        if (
            self.toggle_button.isChecked()
            and self.toggle_animation.state() != self.toggle_animation.State.Running
        ):
            _layout = self.content_area.layout()
            if _layout is None:
                logger.warning("Content area has no layout.")
                return
            content_height = _layout.sizeHint().height()
            self.setMinimumHeight(self.collapsed_height + content_height)
            self.setMaximumHeight(self.collapsed_height + content_height)
            self.content_area.setMaximumHeight(content_height)
        self.updateGeometry()
        p = self.parent()
        if isinstance(p, ScrollArea):
            p.resized.emit()

    def setContentLayout(self, layout: QLayout) -> None:
        lay = self.content_area.layout()
        del lay
        self.content_area.setLayout(layout)
        self.collapsed_height = collapsed_height = (
            self.sizeHint().height() - self.content_area.maximumHeight()
        )
        content_height = layout.sizeHint().height()
        for i in range(self.toggle_animation.animationCount() - 1):
            animation = cast(
                QtCore.QPropertyAnimation, self.toggle_animation.animationAt(i)
            )
            animation.setDuration(self.duration)
            animation.setStartValue(collapsed_height)
            animation.setEndValue(collapsed_height + content_height)

        content_animation = cast(
            QtCore.QPropertyAnimation,
            self.toggle_animation.animationAt(
                self.toggle_animation.animationCount() - 1
            ),
        )
        content_animation.setDuration(self.duration)
        content_animation.setStartValue(0)
        content_animation.setEndValue(content_height)
