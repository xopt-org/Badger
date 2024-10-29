import multiprocessing
import time

import pandas as pd
import pytest


class TestCore:
    """
    This class is to provide unit test coverage for the core.py file.
    """

    @pytest.fixture
    def process_manager(self):
        from badger.gui.default.components.create_process import CreateProcess
        from badger.gui.default.components.process_manager import ProcessManager

        process_manager = ProcessManager()
        process_builder = CreateProcess()
        process_builder.subprocess_prepared.connect(process_manager.add_to_queue)
        process_builder.create_subprocess()

        yield process_manager

        process_manager.close_proccesses()

    @pytest.fixture(scope="session")
    def init_multiprocessing(self):
        multiprocessing.set_start_method("fork", force=True)

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

    def test_run_routine_subprocess(
        self, process_manager, init_multiprocessing
    ) -> None:
        """
        A unit test to ensure the core functionality
        of run_routine_xopt is functioning as intended.
        """
        from badger.db import save_routine
        from badger.tests.utils import create_routine, fix_db_path_issue

        fix_db_path_issue()
        self.count = 0
        self.num_of_points = 3

        self.routine = create_routine()
        time.sleep(1)
        save_routine(self.routine)
        self.termination_condition = {
            "tc_idx": 0,
            "max_eval": 3,
        }
        process_with_args = process_manager.remove_from_queue()
        pause_event = process_with_args["pause_event"]
        data_queue = process_with_args["data_queue"]
        wait_event = process_with_args["wait_event"]
        routine_process = process_with_args["process"]
        data_queue = process_with_args["data_queue"]
        evaluate_queue = process_with_args["evaluate_queue"]

        arg_dict = {
            "routine_id": self.routine.id,
            "routine_name": self.routine.name,
            "variable_ranges": self.routine.vocs.variables,
            "initial_points": self.routine.initial_points,
            "evaluate": True,
            "termination_condition": self.termination_condition,
            "start_time": time.time(),
        }

        data_queue.put(arg_dict)
        wait_event.set()
        pause_event.set()

        time.sleep(0.20)
        routine_process.terminate()
        time.sleep(1)

        while evaluate_queue[1].poll():
            self.results = evaluate_queue[1].recv()

        # assert len(self.candidates_list) == self.count - 1

        assert len(self.results) == self.num_of_points

        assert self.states is None

        """
        path = "./test.yaml"
        assert os.path.exists(path) is True
        os.remove("./test.yaml")
        """

    def test_convert_to_solution(self) -> None:
        pass

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

    def test_run_turbo(self, process_manager, init_multiprocessing) -> None:
        """
        A unit test to ensure TuRBO can run in Badger.
        """
        return

        from badger.db import save_routine
        from badger.tests.utils import create_routine_turbo

        self.count = 0
        self.num_of_points = 3
        self.routine = create_routine_turbo()
        time.sleep(1)
        assert self.routine.generator.turbo_controller.best_value is None
        save_routine(self.routine)
        self.termination_condition = {
            "tc_idx": 0,
            "max_eval": 3,
        }
        process_with_args = process_manager.remove_from_queue()
        pause_event = process_with_args["pause_event"]
        data_queue = process_with_args["data_queue"]
        wait_event = process_with_args["wait_event"]
        routine_process = process_with_args["process"]
        data_queue = process_with_args["data_queue"]
        evaluate_queue = process_with_args["evaluate_queue"]

        arg_dict = {
            "routine_id": self.routine.id,
            "evaluate": True,
            "termination_condition": self.termination_condition,
            "start_time": time.time(),
        }

        data_queue.put(arg_dict)
        wait_event.set()
        pause_event.set()

        time.sleep(0.20)
        routine_process.terminate()
        time.sleep(1)

        while evaluate_queue[1].poll():
            self.results = evaluate_queue[1].recv()

        # assert len(self.candidates_list) == self.count - 1

        # assert len(self.results) == self.num_of_points

        assert self.states is None

        """
        path = "./test.yaml"
        assert os.path.exists(path) is True
        os.remove("./test.yaml")
        """
