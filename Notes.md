# Extension Flow

## Start of Extension

There is only 1 function that handles both initialization and updates to the extension

extensions_palette.py

```python
def add_child_window_to_monitor(self, child_window: AnalysisExtension):
        """
        Add a child window to the run monitor.

        Parameters
        ----------
        child_window : AnalysisExtension
            The child window (extension) to add to the run monitor.

        """
        child_window.window_closed.connect(self.run_monitor.extension_window_closed)
        self.run_monitor.active_extensions.append(child_window)

        try:
            if self.run_monitor.routine is not None:
                child_window.update_window(self.run_monitor.routine)
        except ValueError:
            QMessageBox.warning(
                self, "Extension is not applicable!", traceback.format_exc()
            )
            self.run_monitor.active_extensions.remove(child_window)
            return

        child_window.show()

        self.update_palette()
```
