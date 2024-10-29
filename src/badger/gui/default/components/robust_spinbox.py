from PyQt5.QtWidgets import QDoubleSpinBox, QAbstractSpinBox
from PyQt5.QtCore import Qt
from badger.gui.default.utils import MouseWheelWidgetAdjustmentGuard


class RobustSpinBox(QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        try:
            decimals = kwargs["decimals"]
            del kwargs["decimals"]
        except:
            decimals = 4

        try:
            lb = kwargs["lower_bound"]
            del kwargs["lower_bound"]
            if lb is None:
                lb = -1e3
        except:
            lb = -1e3

        try:
            ub = kwargs["upper_bound"]
            del kwargs["upper_bound"]
            if ub is None:
                ub = 1e3
        except:
            ub = 1e3

        try:
            default_value = kwargs["default_value"]
            del kwargs["default_value"]
            if default_value is None:
                default_value = 0
        except:
            default_value = 0

        super().__init__(*args, **kwargs)

        self.setDecimals(decimals)
        self.setFocusPolicy(Qt.StrongFocus)
        self.installEventFilter(MouseWheelWidgetAdjustmentGuard(self))
        self.setRange(lb, ub)
        self.setStepType(QAbstractSpinBox.AdaptiveDecimalStepType)
        self.setValue(default_value)
