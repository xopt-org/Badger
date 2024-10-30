import os
import pytest
import pandas as pd
from badger.errors import BadgerRunTerminated


class TestCore:
    """
    This class is to provide unit test coverage for the core.py file.
    """

    @pytest.fixture(autouse=True, scope="function")
    def test_core_setup(self, *args, **kwargs) -> None:
        super(TestCore, self).__init__(*args, **kwargs)
        self.count = 0
        self.candidates = None
        self.points_eval_list = []
        self.candidates_list = []
        self.states = None

        data = {"x0": [0.5], "x1": [0.5], "x2": [0.5], "x3": [0.5]}
        data_eval_target = {
            "x0": [0.5],
            "x1": [0.5],
            "x2": [0.5],
            "x3": [0.5],
            "f": [5.0],
        }

        self.points = pd.DataFrame(data)

        self.points_eval_target = pd.DataFrame(data_eval_target)

    def mock_active_callback(self) -> int:
        """
        A mock active callback method to test
        if active callback is functioning properly.
        """
        if self.count >= 5:
            return 2
        else:
            return 0

    def mock_generate_callback(self, candidates: pd.DataFrame) -> None:
        """
        A mock generate callback method to test
        if generate callback is functioning properly.
        """
        self.candidates_list.append(candidates)

    def mock_evaluate_callback(self, points_eval: pd.DataFrame) -> None:
        """
        A mock evaluate callback method to test
        if evaluate callback is functioning properly.
        """
        self.points_eval_list.append(points_eval)
        self.count += 1

    def mock_states_callback(self, states: dict) -> None:
        """
        A mock states callback method to test
        if states callback is functioning properly.
        """
        self.states = states

    def mock_dump_file_callback(self) -> str:
        """
        A mock dump file callback method to test
        if dump file callback is functioning properly.
        """
        return "test.yaml"

    def test_run_routine(self) -> None:
        """
        A unit test to ensure the core functionality
        of run_routine_xopt is functioning as intended.
        """
        from badger.core import run_routine
        from badger.tests.utils import create_routine

        routine = create_routine()

        self.count = 0

        with pytest.raises(BadgerRunTerminated):
            run_routine(
                routine,
                self.mock_active_callback,
                self.mock_generate_callback,
                self.mock_evaluate_callback,
                self.mock_states_callback,
                self.mock_dump_file_callback,
            )

        assert len(self.candidates_list) == self.count - 1
        assert len(self.points_eval_list) == self.count

        assert self.states is None

        path = "./test.yaml"
        assert os.path.exists(path) is True
        os.remove("./test.yaml")

    def test_evaluate_points(self) -> None:
        """
        A unit test to ensure the core functionality of evaluate_points
        is functioning as intended.
        """
        from badger.tests.utils import create_routine

        routine = create_routine()

        assert routine.environment.get_variables(["x1", "x2"]) == {
            "x1": 0.5,
            "x2": 0.5,
        }
        evaluate_points_result = routine.evaluate_data(self.points)

        vocs_list = ["x0", "x1", "x2", "x3", "f"]
        assert (
            evaluate_points_result[vocs_list]
            .astype(float)
            .equals(self.points_eval_target.astype(float))
        )

    def test_run_turbo(self) -> None:
        """
        A unit test to ensure TuRBO can run in Badger.
        """
        from badger.core import run_routine
        from badger.tests.utils import create_routine_turbo

        routine = create_routine_turbo()
        assert routine.generator.turbo_controller.best_value is None

        self.count = 0

        with pytest.raises(BadgerRunTerminated):
            run_routine(
                routine,
                self.mock_active_callback,
                self.mock_generate_callback,
                self.mock_evaluate_callback,
                self.mock_states_callback,
                dump_file_callback=None,
            )

        assert len(self.candidates_list) == self.count - 1
        assert len(self.points_eval_list) == self.count
