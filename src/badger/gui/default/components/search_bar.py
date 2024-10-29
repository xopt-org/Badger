from PyQt5.QtWidgets import QLineEdit


def search_bar():
    # completer = QCompleter(word_list)

    line_edit = QLineEdit()
    line_edit.setPlaceholderText("Search")
    # line_edit.setCompleter(completer)

    return line_edit
