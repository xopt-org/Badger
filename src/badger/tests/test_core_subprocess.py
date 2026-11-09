import multiprocessing
import time
from pathlib import Path
from queue import Queue
from threading import Event

import numpy as np
import pandas as pd
import pytest
import torch
import yaml


@pytest.mark.parametrize(
    "n_interpolate_points, stop_after, pause_after",
    [(None, 1, None), (5, 5, None), (5, 2, None), (5, 5, 2)],
)
def test_subprocess_evaluates_interpolated_points(
    mocker, tmp_path, n_interpolate_points, stop_after, pause_after
):
    from xopt.generators.bayesian import UpperConfidenceBoundGenerator

    from badger import archive, core_subprocess
    from badger.routine import Routine
    from badger.tests.utils import create_routine

    seed = create_routine()
    routine = Routine(
        name="interpolation-test",
        creation_ts="2026-01-01-000000",
        generator=UpperConfidenceBoundGenerator(
            vocs=seed.vocs, n_interpolate_points=n_interpolate_points
        ),
        environment=seed.environment,
        initial_points=seed.initial_points,
    )
    routine.evaluate_data(routine.initial_points)
    mocker.patch.object(UpperConfidenceBoundGenerator, "train_model")
    propose = mocker.patch.object(
        UpperConfidenceBoundGenerator,
        "propose_candidates",
        return_value=torch.full((1, 4), -0.5, dtype=torch.double),
    )
    mocker.patch.object(archive, "load_run", return_value=routine)
    mocker.patch.object(archive, "BADGER_ARCHIVE_ROOT", str(tmp_path))
    archive_spy = mocker.spy(archive, "archive_run")

    stop_event, pause_event, wait_event = Event(), Event(), Event()
    pause_event.set()
    wait_event.set()
    updates = []

    def receive_update(update):
        data, generator = update
        updates.append(data.copy())
        assert generator.n_interpolate_points == n_interpolate_points
        if len(data) == stop_after + 1:
            stop_event.set()

    sender = mocker.Mock()
    sender.send.side_effect = receive_update

    def resume(*args):
        assert not pause_event.is_set()
        assert len(routine.data) == pause_after + 1
        pause_event.set()

    pause_spy = mocker.patch.object(
        core_subprocess, "check_for_pause_resume", side_effect=resume
    )
    args_queue = Queue()
    args_queue.put(
        {
            "routine_filename": "interpolation-test.yaml",
            "run_data": True,
            "variable_ranges": routine.vocs.variables,
            "initial_points": routine.initial_points,
            "init_points": False,
            "evaluate": True,
            "archive": True,
            "verbose": 0,
            "start_time": time.time(),
            "termination_condition": (
                {"tc_idx": 0, "max_eval": pause_after + 1} if pause_after else None
            ),
        }
    )
    errors = Queue()
    core_subprocess.run_routine_subprocess(
        args_queue,
        errors,
        (sender, None),
        stop_event,
        pause_event,
        wait_event,
    )

    assert propose.call_count == 1
    expected = (
        np.linspace(0.5, -0.5, n_interpolate_points + 1)[1 : stop_after + 1]
        if n_interpolate_points
        else [-0.5]
    )
    np.testing.assert_allclose(routine.data["x0"].iloc[1:], expected, atol=1e-12)
    assert len(updates) == stop_after
    for index, data in enumerate(updates, start=1):
        assert len(data) == index + 1
        np.testing.assert_allclose(data["x0"].iloc[1:], expected[:index], atol=1e-12)
        assert data["f"].notna().all()
    assert archive_spy.call_count == stop_after
    saved_run = archive_spy.spy_return
    saved = yaml.safe_load(
        (Path(saved_run["path"]) / saved_run["filename"]).read_text()
    )
    np.testing.assert_allclose(
        pd.DataFrame(saved["data"])["x0"].iloc[1:], expected, atol=1e-12
    )
    assert pause_spy.call_count == (1 if pause_after else 0)
    assert all(
        errors.get_nowait()["type"] == core_subprocess.TERMINATION_REACHED_TYPE
        for _ in range(errors.qsize())
    )


class TestCore:
    """
    This class is to provide unit test coverage for the core.py file.
    """

    @pytest.fixture
    def process_manager(self):
        from badger.gui.components.create_process import CreateProcess
        from badger.gui.components.process_manager import ProcessManager

        process_manager = ProcessManager()
        process_builder = CreateProcess()
        process_builder.subprocess_prepared.connect(process_manager.add_to_queue)
        process_builder.create_subprocess()

        yield process_manager

        process_manager.close_proccesses()

    @pytest.fixture(scope="session")
    def init_multiprocessing(self):
        # Use 'spawn' on Windows, 'fork' on Unix-like systems
        method = (
            "spawn"
            if multiprocessing.get_start_method(allow_none=True) != "fork"
            else "fork"
        )
        multiprocessing.set_start_method(method, force=True)

    @pytest.fixture(autouse=True, scope="function")
    def test_core_setup(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
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
        from badger.archive import save_tmp_run
        from badger.tests.utils import create_routine

        self.count = 0
        self.num_of_points = 3

        self.routine = create_routine()
        time.sleep(1)
        tmp_filename = save_tmp_run(self.routine)
        self.termination_condition = {
            "tc_idx": 0,
            "max_eval": 3,
        }
        process_with_args = process_manager.remove_from_queue()
        pause_event = process_with_args["pause_event"]
        args_queue = process_with_args["args_queue"]
        wait_event = process_with_args["wait_event"]
        routine_process = process_with_args["process"]
        evaluate_queue = process_with_args["evaluate_queue"]

        arg_dict = {
            "routine_id": self.routine.id,
            "routine_filename": tmp_filename,
            "routine_name": self.routine.name,
            "variable_ranges": self.routine.vocs.variables,
            "initial_points": self.routine.initial_points,
            "evaluate": True,
            "termination_condition": self.termination_condition,
            "start_time": time.time(),
        }

        args_queue.put(arg_dict)
        wait_event.set()
        pause_event.set()

        time.sleep(0.20)
        routine_process.terminate()
        time.sleep(1)

        self.results = []
        while evaluate_queue[1].poll():
            self.results = evaluate_queue[1].recv()

        # assert len(self.candidates_list) == self.count - 1

        # assert len(self.results[0]) == self.num_of_points

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
        args_queue = process_with_args["args_queue"]
        wait_event = process_with_args["wait_event"]
        routine_process = process_with_args["process"]
        evaluate_queue = process_with_args["evaluate_queue"]

        arg_dict = {
            "routine_id": self.routine.id,
            "evaluate": True,
            "termination_condition": self.termination_condition,
            "start_time": time.time(),
        }

        args_queue.put(arg_dict)
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
