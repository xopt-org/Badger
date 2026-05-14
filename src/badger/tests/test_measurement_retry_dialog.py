from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QDialog


def test_measurement_retry_dialog_retry(qtbot):
    from badger.gui.windows.measurement_retry_dialog import (
        BadgerMeasurementRetryDialog,
    )

    dialog = BadgerMeasurementRetryDialog(text="Test error", detailedText="traceback")
    qtbot.addWidget(dialog)
    assert "Test error" in dialog.textLabel.text()
    assert "traceback" in dialog.detailedTextWidget.toPlainText()
    QTimer.singleShot(0, dialog.retryButton.click)
    assert dialog.exec_() == QDialog.Accepted


def test_measurement_retry_dialog_stop(qtbot):
    from badger.gui.windows.measurement_retry_dialog import (
        BadgerMeasurementRetryDialog,
    )

    dialog = BadgerMeasurementRetryDialog(text="Test error", detailedText="traceback")
    qtbot.addWidget(dialog)
    assert "Test error" in dialog.textLabel.text()
    assert "traceback" in dialog.detailedTextWidget.toPlainText()
    QTimer.singleShot(0, dialog.stopButton.click)
    assert dialog.exec_() == QDialog.Rejected
