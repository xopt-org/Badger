from PyQt5.QtTest import QSignalSpy


class TestSmartRunController:
    @staticmethod
    def create_controller():
        # Create a fresh controller so each test starts without prior run state.
        from badger.gui.mini.components.run_controller import SmartRunController

        return SmartRunController()

    def test_pauses_active_run(self, qtbot):
        # An active, unpaused run should pause instead of stopping or restarting.
        controller = self.create_controller()
        pause_spy = QSignalSpy(controller.sig_pause_ctrl)
        stop_spy = QSignalSpy(controller.sig_stop)
        start_spy = QSignalSpy(controller.sig_start)

        controller.smart_run({"name": "routine"}, True, False, False)

        # The pause spy captures the requested pause state; no restart signals are allowed.
        assert len(pause_spy) == 1
        assert pause_spy[0][0] is True
        assert len(stop_spy) == 0
        assert len(start_spy) == 0

    def test_resumes_unchanged_paused_run(self, qtbot):
        # Pressing run for the unchanged paused routine should unpause it.
        controller = self.create_controller()
        routine = {"name": "routine"}
        controller.last_routine_dict = routine
        pause_spy = QSignalSpy(controller.sig_pause_ctrl)

        controller.smart_run(routine, True, True, False)

        # A single False payload confirms that the paused run was resumed.
        assert len(pause_spy) == 1
        assert pause_spy[0][0] is False

    def test_restarts_unchanged_finished_run_with_data(self, qtbot):
        # An unchanged routine with no active process should restart using its data.
        controller = self.create_controller()
        routine = {"name": "routine"}
        controller.last_routine_dict = routine
        start_spy = QSignalSpy(controller.sig_start)

        controller.smart_run(routine, False, False, False)

        # The start signal's True payload means the previous displayed data is reused.
        assert len(start_spy) == 1
        assert start_spy[0][0] is True
        assert controller.last_routine_dict == routine

    def test_queues_compatible_restart_with_data(self, qtbot):
        # A compatible edit during a paused run should stop first, then restart with data.
        controller = self.create_controller()
        controller.last_routine_dict = {"name": "old"}
        stop_spy = QSignalSpy(controller.sig_stop)
        start_spy = QSignalSpy(controller.sig_start)

        controller.smart_run({"name": "new"}, True, True, True)

        # Stop is emitted first, while the flags prove the compatible restart is queued with data.
        assert len(stop_spy) == 1
        assert len(start_spy) == 0
        assert controller._pending_start is True
        assert controller._load_data is True

        controller.notify_routine_finished()

        # Completion releases the queued start and carries the data-loading choice through the signal.
        assert len(start_spy) == 1
        assert start_spy[0][0] is True
        assert controller._pending_start is False
        assert controller.last_routine_dict == {"name": "new"}

    def test_starts_compatible_finished_run_with_data(self, qtbot):
        # A compatible edit after a run ends can start immediately with existing data.
        controller = self.create_controller()
        controller.last_routine_dict = {"name": "old"}
        start_spy = QSignalSpy(controller.sig_start)

        controller.smart_run({"name": "new"}, False, False, True)

        # With no active process, a compatible restart starts immediately and requests displayed data.
        assert len(start_spy) == 1
        assert start_spy[0][0] is True

    def test_queues_incompatible_restart_without_data(self, qtbot):
        # An incompatible edit during a paused run should queue a fresh restart.
        controller = self.create_controller()
        controller.last_routine_dict = {"name": "old"}
        stop_spy = QSignalSpy(controller.sig_stop)
        start_spy = QSignalSpy(controller.sig_start)

        controller.smart_run({"name": "new"}, True, True, False)

        # Stop is emitted while pending state records that this incompatible restart must start fresh.
        assert len(stop_spy) == 1
        assert len(start_spy) == 0
        assert controller._pending_start is True
        assert controller._load_data is False

        controller.notify_routine_finished()

        # The queued restart emits False, proving that old displayed data is not loaded.
        assert len(start_spy) == 1
        assert start_spy[0][0] is False

    def test_starts_incompatible_finished_run_without_data(self, qtbot):
        # An incompatible edit after a run ends should start without previous data.
        controller = self.create_controller()
        controller.last_routine_dict = {"name": "old"}
        start_spy = QSignalSpy(controller.sig_start)

        controller.smart_run({"name": "new"}, False, False, False)

        # The immediate start uses a False payload because the routine is incompatible.
        assert len(start_spy) == 1
        assert start_spy[0][0] is False

    def test_restart_override_starts_fresh_run_and_resets_flag(self, qtbot):
        # The override bypasses routine matching and is consumed by the next run request.
        controller = self.create_controller()
        routine = {"name": "routine"}
        controller.last_routine_dict = routine
        controller.set_restart_override_flag()
        start_spy = QSignalSpy(controller.sig_start)

        controller.smart_run(routine, False, False, True)

        # The override forces a fresh start despite matching routine data, then clears itself.
        assert len(start_spy) == 1
        assert start_spy[0][0] is False
        assert controller.restart_override_flag is False

    def test_notify_finished_does_nothing_without_pending_run(self, qtbot):
        # Completion notifications must not start a run when none was queued.
        controller = self.create_controller()
        start_spy = QSignalSpy(controller.sig_start)

        controller.notify_routine_finished()

        # An empty start spy confirms that completion is ignored without a queued restart.
        assert len(start_spy) == 0

    def test_start_run_records_new_routine_and_clears_pending_state(self, qtbot):
        # Starting a queued run records its routine and clears the pending marker.
        controller = self.create_controller()
        routine = {"name": "routine"}
        controller._new_routine_dict = routine
        controller._pending_start = True
        start_spy = QSignalSpy(controller.sig_start)

        controller.start_run(True)

        # The signal payload and state fields confirm the queued routine was started with its data.
        assert len(start_spy) == 1
        assert start_spy[0][0] is True
        assert controller._pending_start is False
        assert controller.last_routine_dict == routine
