import pytest


@pytest.fixture
def process_manager():
    from badger.gui.default.components.process_manager import ProcessManager

    return ProcessManager()


class TestProcessManager:
    def test_add_to_queue(self, process_manager):
        """
        Test that a process can be added to the queue.
        """
        process_with_args = {"process": "test_process", "args": [1, 2, 3]}
        process_manager.add_to_queue(process_with_args)
        assert len(process_manager.processes_queue) == 1
        assert process_manager.processes_queue[0] == process_with_args

    def test_remove_from_queue(self, process_manager, qtbot):
        """
        Test that a process can be removed from the queue and the correct process is returned.
        """
        process_with_args1 = {"process": "test_process_one", "args": [1, 2, 3]}
        process_with_args2 = {"process": "test_process_two", "args": [4, 5, 6]}
        process_manager.add_to_queue(process_with_args1)
        process_manager.add_to_queue(process_with_args2)

        removed_process = process_manager.remove_from_queue()
        assert removed_process == process_with_args1
        assert len(process_manager.processes_queue) == 1
        removed_process = process_manager.remove_from_queue()
        assert removed_process == process_with_args2
        removed_process = process_manager.remove_from_queue()
        assert removed_process is None
        assert len(process_manager.processes_queue) == 0

        process_manager.add_to_queue(process_with_args1)

        with qtbot.waitSignal(process_manager.processQueueUpdated) as blocker:
            process_manager.remove_from_queue()

        assert blocker.signal_triggered
