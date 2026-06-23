"""Widget for visualizing hard bounds, preview scan bounds, and current value."""

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QPaintEvent
from PyQt5.QtWidgets import QWidget


class BoundsPreviewBar(QWidget):
    """Compact bar that visualizes hard bounds, preview bounds, and current value."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize default bounds and display settings."""
        super().__init__(parent)
        self.hard_lower = 0.0
        self.hard_upper = 1.0
        self.curr = 0.0
        self.preview_lower = 0.0
        self.preview_upper = 0.0

        self.setMinimumHeight(32)

    def set_values(
        self,
        hard_lower: float,
        hard_upper: float,
        curr: float,
        preview_lower: float,
        preview_upper: float,
    ) -> None:
        """Update displayed values and request a repaint."""
        self.curr = curr

        # make sure bounds are correctly upper/lower
        self.hard_lower = min(hard_lower, hard_upper)
        self.hard_upper = max(hard_lower, hard_upper)
        self.preview_lower = min(preview_lower, preview_upper)
        self.preview_upper = max(preview_lower, preview_upper)

        self.update()

    def _to_x(self, value: float, left: float, width: float) -> float:
        """Map a value onto the horizontal track coordinate."""
        if self.hard_upper == self.hard_lower:
            # render with min width
            return left + width * 0.5
        # convert value to relative width along bar
        ratio = (value - self.hard_lower) / (self.hard_upper - self.hard_lower)
        ratio = max(0.0, min(1.0, ratio))
        return left + ratio * width

    def paintEvent(self, _event: QPaintEvent) -> None:
        """Paint the track, preview range, current marker, and value labels."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # draw full range
        rect = self.rect()
        track_margin = 5
        left = float(rect.left() + track_margin)
        right = float(rect.right())
        track_y = float(rect.center().y() - 5)
        track_h = 10  # height
        track_w = max(1.0, right - left)
        track_top = track_y - track_h / 2.0
        track_rect = QRectF(left, track_top, track_w, float(track_h))

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(55, 66, 81)))
        painter.drawRoundedRect(track_rect, 2, 2)

        # draw bounds preview
        start_x = self._to_x(self.preview_lower, left, track_w)
        end_x = self._to_x(self.preview_upper, left, track_w)
        preview_left = min(start_x, end_x)  # make sure bounds stay within rectangle
        preview_right = max(start_x, end_x)
        preview_w = max(2.0, preview_right - preview_left)
        preview_rect = QRectF(preview_left, track_top, preview_w, float(track_h))
        painter.setBrush(QBrush(QColor(37, 154, 233)))
        painter.drawRoundedRect(preview_rect, 1, 1)

        # current line
        curr_x = int(round(self._to_x(self.curr, left, track_w)))
        painter.setPen(QPen(QColor(240, 240, 240), 1))
        painter.drawLine(
            curr_x, int(round(track_top)), curr_x, int(round(track_top + track_h))
        )

        # text labels
        font = painter.font()
        font.setPointSizeF(10.0)
        painter.setFont(font)
        painter.setPen(QPen(QColor(190, 190, 190), 1))
        label_y = int(round(track_top + track_h + 12))
        painter.drawText(int(round(left)), label_y, f"{self.hard_lower:.2f}")
        painter.drawText(
            int(round(max(left, right - 28))), label_y, f"{self.hard_upper:.2f}"
        )
        painter.drawText(
            int(round(max(left, curr_x - 16))), label_y, f"{self.curr:.3f}"
        )
