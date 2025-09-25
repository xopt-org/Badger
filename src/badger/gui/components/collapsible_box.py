from PyQt5 import QtCore, QtGui, QtWidgets


stylesheet_toolbutton = """
QToolButton
{
    border: none;
}
"""


# https://stackoverflow.com/a/56293688
class ScrollArea(QtWidgets.QScrollArea):
    resized = QtCore.pyqtSignal()

    def resizeEvent(self, e):
        self.resized.emit()
        return super(ScrollArea, self).resizeEvent(e)


# https://stackoverflow.com/a/52617714/4263605
class CollapsibleBox(QtWidgets.QWidget):
    def __init__(self, parent=None, title="", duration=100, tooltip=None):
        super(CollapsibleBox, self).__init__(parent)

        self.title = title
        self.duration = duration

        cool_font = QtGui.QFont()
        cool_font.setWeight(QtGui.QFont.DemiBold)
        cool_font.setPixelSize(13)

        self.toggle_button = QtWidgets.QToolButton(
            text=title, checkable=True, checked=False
        )
        self.toggle_button.setFont(cool_font)
        self.toggle_button.setFixedHeight(28)
        self.toggle_button.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
        self.toggle_button.setStyleSheet(stylesheet_toolbutton)
        self.toggle_button.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.toggle_button.setIconSize(QtCore.QSize(11, 11))
        self.toggle_button.setArrowType(QtCore.Qt.RightArrow)
        self.toggle_button.setToolTip(tooltip)
        self.toggle_button.clicked.connect(self.start_animation)
        # self.toggle_button.setText(f'+ {title}')

        self.toggle_animation = QtCore.QParallelAnimationGroup(self)

        self.content_area = ScrollArea(maximumHeight=0, minimumHeight=0)
        self.content_area.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed
        )
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
    def start_animation(self):
        checked = self.toggle_button.isChecked()
        arrow_type = QtCore.Qt.DownArrow if checked else QtCore.Qt.RightArrow
        self.toggle_button.setArrowType(arrow_type)
        # self.toggle_button.setText(f'- {self.title}' if not checked else f'+ {self.title}')
        direction = (
            QtCore.QAbstractAnimation.Forward
            if checked
            else QtCore.QAbstractAnimation.Backward
        )
        self.toggle_animation.setDirection(direction)
        self.toggle_animation.start()

    def expand(self):
        if not self.toggle_button.isChecked():
            self.toggle_button.click()

    def updateContentLayout(self):
        if (
            self.toggle_button.isChecked()
            and self.toggle_animation.state() != self.toggle_animation.Running
        ):
            content_height = self.content_area.layout().sizeHint().height()
            self.setMinimumHeight(self.collapsed_height + content_height)
            self.setMaximumHeight(self.collapsed_height + content_height)
            self.content_area.setMaximumHeight(content_height)
        self.updateGeometry()
        p = self.parent()
        if isinstance(p, ScrollArea):
            p.resized.emit()

    def setContentLayout(self, layout):
        lay = self.content_area.layout()
        del lay
        self.content_area.setLayout(layout)
        self.collapsed_height = collapsed_height = (
            self.sizeHint().height() - self.content_area.maximumHeight()
        )
        content_height = layout.sizeHint().height()
        for i in range(self.toggle_animation.animationCount() - 1):
            animation = self.toggle_animation.animationAt(i)
            animation.setDuration(self.duration)
            animation.setStartValue(collapsed_height)
            animation.setEndValue(collapsed_height + content_height)

        content_animation = self.toggle_animation.animationAt(
            self.toggle_animation.animationCount() - 1
        )
        content_animation.setDuration(self.duration)
        content_animation.setStartValue(0)
        content_animation.setEndValue(content_height)
