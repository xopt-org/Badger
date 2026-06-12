from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAbstractSpinBox, QDoubleSpinBox, QWidget

from badger.gui.utils import MouseWheelWidgetAdjustmentGuard


class RobustSpinBox(QDoubleSpinBox):
    def __init__(
        self,
        parent: QWidget | None = None,
        decimals: int = 6,
        lower_bound: float = -1e3,
        upper_bound: float = 1e3,
        default_value: float = 0,
    ) -> None:
        super().__init__(parent)

        self.setDecimals(decimals)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.installEventFilter(MouseWheelWidgetAdjustmentGuard(self))
        self.setRange(lower_bound, upper_bound)
        self.setStepType(QAbstractSpinBox.StepType.AdaptiveDecimalStepType)
        self.setValue(default_value)
