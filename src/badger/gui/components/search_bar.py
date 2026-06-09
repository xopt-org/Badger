"""Search bar factory for the Badger GUI. Creates a simple QLineEdit with
placeholder text for filtering routine lists and other searchable collections
in the interface."""

from PyQt5.QtWidgets import QLineEdit


def search_bar():
    # completer = QCompleter(word_list)

    line_edit = QLineEdit()
    line_edit.setPlaceholderText("Search")
    # line_edit.setCompleter(completer)

    return line_edit
