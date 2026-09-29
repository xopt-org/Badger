"""Creates a compact label + QLineEdit pair used throughout the GUI for
key-value fields."""

from PyQt5.QtWidgets import QHBoxLayout, QLabel, QLineEdit, QWidget


def labeled_lineedit(
    name: str,
    text: str,
    width_name: int = 64,
    placeholder: str | None = None,
    readonly: bool = True,
) -> QWidget:
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
