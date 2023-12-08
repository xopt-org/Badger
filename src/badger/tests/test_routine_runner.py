
class TestRoutineRunner:
    def test_routine_runner(self, qtbot):
        from badger.gui.default.components.routine_runner import BadgerRoutineRunner
        from badger.tests.utils import create_routine

        routine = create_routine()

        runner = BadgerRoutineRunner(routine, False)
        runner.set_termination_condition({"tc_idx": 0, "max_eval": 2})

        runner.run()
        assert len(runner.routine.data) == 2

        # TODO: check for signal emit message
