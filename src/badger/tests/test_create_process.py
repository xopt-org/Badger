import multiprocessing as mp
import sys
from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtWidgets import QApplication

app = QApplication(sys.argv)


@pytest.fixture
def process_creator():
    from badger.gui.default.components.create_process import CreateProcess

    return CreateProcess()


def test_create_subprocess_emits_signals(qtbot, process_creator):
    with (
        patch("badger.gui.default.components.create_process.Process") as mock_process,
        patch("badger.gui.default.components.create_process.run_routine_subprocess"),
    ):
        mock_process.return_value = MagicMock()

        with (
            qtbot.waitSignal(
                process_creator.subprocess_prepared
            ) as blocker_subprocess_prepared,
            qtbot.waitSignal(process_creator.finished) as blocker_finished,
        ):
            process_creator.create_subprocess()

        assert blocker_subprocess_prepared.signal_triggered
        assert blocker_finished.signal_triggered
        mock_process.assert_called_once()

        # Verify that the emitted object contains the expected keys
        emitted_args = blocker_subprocess_prepared.args[0]
        assert set(emitted_args.keys()) == {
            "process",
            "stop_event",
            "pause_event",
            "data_queue",
            "evaluate_queue",
            "wait_event",
        }

        assert isinstance(emitted_args["data_queue"], mp.queues.Queue)
        assert isinstance(emitted_args["evaluate_queue"], tuple)
        assert isinstance(emitted_args["wait_event"], mp.synchronize.Event)
        assert isinstance(emitted_args["stop_event"], mp.synchronize.Event)
        assert isinstance(emitted_args["pause_event"], mp.synchronize.Event)
