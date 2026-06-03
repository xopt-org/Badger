"""Factory function for creating labeled line-edit widgets. Produces a compact
horizontal widget pairing a fixed-width label with a QLineEdit, used
throughout the Badger GUI for displaying read-only or editable key-value
fields."""

from PyQt5.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget


def labeled_lineedit(name, text, width_name=64, placeholder=None, readonly=True):
    widget = QWidget()
    hbox = QHBoxLayout(widget)
    hbox.setContentsMargins(0, 0, 0, 0)
    label = QLabel(name)
    label.setFixedWidth(width_name)
    widget.edit = edit = QLineEdit()
    if readonly:
        edit.setReadOnly(readonly)
    edit.setText(text)
    if placeholder:
        edit.setPlaceholderText(placeholder)

    hbox.addWidget(label)
    hbox.addWidget(edit, 1)

    return widget
