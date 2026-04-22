# https://stackoverflow.com/a/67628976/4263605
from PyQt5 import QtCore, QtWidgets, QtGui


class ElidingLabel(QtWidgets.QLabel):
    """Label with text elision.

    QLabel which will elide text too long to fit the widget.  Based on:
    https://doc-snapshots.qt.io/qtforpython-5.15/overviews/qtwidgets-widgets-elidedlabel-example.html

    Parameters
    ----------
    text : str

        Label text.

    mode : QtCore.Qt.TextElideMode

       Specify where ellipsis should appear when displaying texts that
       don't fit.

       Default is QtCore.Qt.ElideMiddle.

       Possible modes:
         QtCore.Qt.ElideLeft
         QtCore.Qt.ElideMiddle
         QtCore.Qt.ElideRight

    parent : QWidget

       Parent widget.  Default is None.

    f : Qt.WindowFlags()

       https://doc-snapshots.qt.io/qtforpython-5.15/PySide2/QtCore/Qt.html#PySide2.QtCore.PySide2.QtCore.Qt.WindowType

    """

    elision_changed = QtCore.pyqtSignal(bool)

    def __init__(self, text="", mode=QtCore.Qt.ElideMiddle, **kwargs):
        super().__init__(**kwargs)

        self._mode = mode
        self.is_elided = False
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred
        )
        self.setText(text)

    def setText(self, text):
        self._contents = text

        # This line set for testing.  Its value is the return value of
        # QFontMetrics.elidedText, set in paintEvent.  The variable
        # must be initialized for testing.  The value should always be
        # the same as contents when not elided.
        self._elided_line = text

        self.update()

    def text(self):
        return self._contents

    def paintEvent(self, event):
        super().paintEvent(event)

        did_elide = False

        painter = QtGui.QPainter(self)
        font_metrics = painter.fontMetrics()
        text_width = font_metrics.horizontalAdvance(self.text())

        # layout phase
        text_layout = QtGui.QTextLayout(self._contents, painter.font())
        text_layout.beginLayout()

        while True:
            line = text_layout.createLine()

            if not line.isValid():
                break

            line.setLineWidth(self.width())

            if text_width >= self.width():
                self._elided_line = font_metrics.elidedText(
                    self._contents, self._mode, self.width()
                )
                painter.drawText(
                    QtCore.QPoint(0, font_metrics.ascent()), self._elided_line
                )
                did_elide = line.isValid()
                break
            else:
                line.draw(painter, QtCore.QPoint(0, 0))

        text_layout.endLayout()

        if did_elide != self.is_elided:
            self.is_elided = did_elide
            self.elision_changed.emit(did_elide)


class SimpleElidedLabel(QtWidgets.QLabel):
    def __init__(self, text="", parent=None):
        super(SimpleElidedLabel, self).__init__(parent)
        self._text = text

    def setText(self, text):
        self._text = text
        super(SimpleElidedLabel, self).setText(self.elidedText())

    def resizeEvent(self, event):
        super(SimpleElidedLabel, self).setText(self.elidedText())
        super(SimpleElidedLabel, self).resizeEvent(event)

    def elidedText(self):
        metrics = QtGui.QFontMetrics(self.font())
        elided = metrics.elidedText(self._text, QtCore.Qt.ElideRight, self.width())
        return elided
