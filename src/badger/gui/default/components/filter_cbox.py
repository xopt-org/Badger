from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QWidget
from PyQt5.QtWidgets import QComboBox, QStyledItemDelegate, QLabel
from badger.gui.default.components.collapsible_box import CollapsibleBox


class BadgerFilterBox(CollapsibleBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.init_ui()

    def init_ui(self):
        vbox = QVBoxLayout()

        # Obj filter
        obj = QWidget()
        hbox_obj = QHBoxLayout(obj)
        hbox_obj.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Objective")
        lbl.setFixedWidth(64)
        self.cb_obj = cb_obj = QComboBox()
        cb_obj.setItemDelegate(QStyledItemDelegate())
        cb_obj.addItems(["", "HXR", "SXR"])
        cb_obj.setCurrentIndex(-1)
        hbox_obj.addWidget(lbl)
        hbox_obj.addWidget(cb_obj, 1)
        vbox.addWidget(obj)

        # Region filter
        region = QWidget()
        hbox_reg = QHBoxLayout(region)
        hbox_reg.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel("Region")
        lbl.setFixedWidth(64)
        self.cb_reg = cb_reg = QComboBox()
        cb_reg.setItemDelegate(QStyledItemDelegate())
        cb_reg.addItems(
            [
                "",
                "LI21:201, 211, 271, 278",
                "LI26:201, 301, 401, 501",
                "LI26:601, 701, 801, 901",
                "IN20:361, 371, 425, 441, 511, 525",
                "LTUH:620, 640, 660, 680",
                "LTUS:620, 640, 660, 680",
            ]
        )
        cb_reg.setCurrentIndex(-1)
        hbox_reg.addWidget(lbl)
        hbox_reg.addWidget(cb_reg, 1)
        vbox.addWidget(region)

        # Gain filter
        gain = QWidget()
        hbox_gain = QHBoxLayout(gain)
        hbox_gain.setContentsMargins(0, 0, 0, 8)
        lbl = QLabel("Gain")
        lbl.setFixedWidth(64)
        self.cb_gain = cb_gain = QComboBox()
        cb_gain.setItemDelegate(QStyledItemDelegate())
        cb_gain.addItems(
            [
                "",
                "1",
                "2",
                "4",
                "8",
            ]
        )
        cb_gain.setCurrentIndex(-1)
        hbox_gain.addWidget(lbl)
        hbox_gain.addWidget(cb_gain, 1)
        vbox.addWidget(gain)

        self.setContentLayout(vbox)
