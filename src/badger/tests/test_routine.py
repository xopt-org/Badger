import os

import pytest


class TestRoutine:
    def test_routine_init(self):
        from badger.tests.utils import create_routine

        routine = create_routine()
        routine.evaluate_data(routine.initial_points)

        assert len(routine.data) == 1

    def test_routine_serialization(self):
        from badger.routine import Routine
        from badger.tests.utils import create_routine

        routine = create_routine()
        routine.evaluate_data(routine.initial_points)
        routine.dump("test.yaml")

        lroutine = Routine.from_file("test.yaml")
        assert lroutine.environment.variable_names == routine.environment.variable_names
        lroutine.evaluate_data(routine.initial_points)

        print(lroutine.data)

        assert len(lroutine.data) == 2

    def test_routine_env_dump(self):
        from badger.environment import Environment
        from badger.routine import Routine
        from badger.tests.utils import create_routine

        routine = create_routine()
        assert isinstance(routine.environment, Environment)

        routine.environment.flag = 1
        assert routine.environment.flag == 1

        routine_str = routine.yaml()
        routine_re = Routine.from_yaml(routine_str)
        assert routine_re.environment.flag == 1

    @pytest.fixture(scope="module", autouse=True)
    def clean_up(self):
        yield
        files = ["test.yaml"]
        for f in files:
            if os.path.exists(f):
                os.remove(f)
