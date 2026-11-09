from PyQt5.QtCore import QUrl


def long_page(name, *_):
    return f"# {name}\n\n" + "line\n\n" * 300


def test_docs_back_button(qtbot, monkeypatch):
    from badger.gui.windows import docs_window
    from badger.gui.windows.docs_window import BadgerDocsWindow

    monkeypatch.setattr(docs_window, "load_badger_docs", long_page)
    window = BadgerDocsWindow(None, "gui-usage")
    qtbot.addWidget(window)
    window.show()
    window.update_docs("gui-usage")
    bar = window.markdown_viewer.verticalScrollBar()
    assert not window.btn_back.isEnabled()

    qtbot.waitUntil(lambda: bar.maximum() > 0)
    bar.setValue(bar.maximum() // 2)
    scroll = bar.value()
    window.handle_link_click(QUrl("/algorithms-overview"))
    assert window.docs_name == "algorithms-overview"
    assert window.btn_back.isEnabled()

    window.go_back()
    assert window.docs_name == "gui-usage"
    qtbot.waitUntil(lambda: bar.value() == scroll)
    assert not window.btn_back.isEnabled()

    window.handle_link_click(QUrl("/history"))
    window.update_docs("gui-usage")  # opened afresh: new history
    assert not window.btn_back.isEnabled()
