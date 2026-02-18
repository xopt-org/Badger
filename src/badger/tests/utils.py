import os
from typing import Any
import numpy as np
import pandas as pd
from xopt import VOCS
from xopt.generators.bayesian import UpperConfidenceBoundGenerator
from xopt.generators import RandomGenerator

from badger.routine import Routine


def create_routine() -> Routine:

    test_routine: dict[str, Any] = {
        "name": "routine-for-core-test",
        "generator": "random",
        "env": "test",
        "generator_params": {},
        "env_params": {},
        "vocs": {
            "variables": {"x0": [-1, 1], "x1": [-1, 1], "x2": [-1, 1], "x3": [-1, 1]},
            "objectives": {"f": "MAXIMIZE"},
            "constraints": {"c": ["GREATER_THAN", 0]},
        },
        "init_points": {"x0": [0.5], "x1": [0.5], "x2": [0.5], "x3": [0.5]},
    }

    vocs = VOCS(**test_routine["vocs"])

    generator = RandomGenerator(vocs=vocs)

    return Routine(
        name="test",
        vocs=vocs,
        generator=generator,
        environment={"name": "test"},
        initial_points=pd.DataFrame(test_routine["init_points"]),
    )


def create_multiobjective_routine() -> Routine:

    test_routine: dict[str, Any] = {
        "name": "routine-for-core-test",
        "generator": "random",
        "generator_params": {},
        "env_params": {},
        "vocs": {
            "variables": {"x0": [-1, 1], "x1": [-1, 1], "x2": [-1, 1], "x3": [-1, 1]},
            "objectives": {"f1": "MAXIMIZE", "f2": "MINIMIZE"},
            "constraints": {},
        },
        "init_points": {"x0": [0.5], "x1": [0.5], "x2": [0.5], "x3": [0.5]},
    }

    vocs = VOCS(**test_routine["vocs"])

    generator = RandomGenerator(vocs=vocs)

    return Routine(
        name="test",
        vocs=vocs,
        generator=generator,
        environment={"name": "multiobjective_test"},
        initial_points=pd.DataFrame(test_routine["init_points"]),
    )


def create_routine_turbo() -> Routine:

    test_routine: dict[str, Any] = {
        "name": "routine-for-turbo-test",
        "generator": "expected_improvement",
        "env": "test",
        "generator_params": {
            "turbo_controller": "optimize",
            "gp_constructor": {
                "name": "standard",
                "use_low_noise_prior": True,
            },
            "beta": 2.0,
        },
        "env_params": {},
        "config": {
            "variables": {"x0": [-1, 1], "x1": [-1, 1], "x2": [-1, 1], "x3": [-1, 1]},
            "objectives": {"f": "MAXIMIZE"},
            "init_points": {"x0": [0.5], "x1": [0.5], "x2": [0.5], "x3": [0.5]},
        },
    }

    vocs = VOCS(
        variables=test_routine["config"]["variables"],
        objectives=test_routine["config"]["objectives"],
    )

    generator = UpperConfidenceBoundGenerator(
        vocs=vocs, **test_routine["generator_params"]
    )

    return Routine(
        name="test-turbo",
        vocs=vocs,
        generator=generator,
        environment={"name": "test"},
        initial_points=pd.DataFrame(test_routine["config"]["init_points"]),
    )


def create_routine_critical() -> Routine:

    test_routine: dict[str, Any] = {
        "name": "routine-for-critical-test",
        "generator": "random",
        "env": "test",
        "generator_params": {},
        "env_params": {},
        "vocs": {
            "variables": {"x0": [-1, 1], "x1": [-1, 1], "x2": [-1, 1], "x3": [-1, 1]},
            "objectives": {"f": "MAXIMIZE"},
            "constraints": {"c": ["LESS_THAN", 0]},
        },
        "init_points": {"x0": [0.5], "x1": [0.5], "x2": [0.5], "x3": [0.5]},
    }

    vocs = VOCS(**test_routine["vocs"])

    generator = RandomGenerator(vocs=vocs)

    return Routine(
        name="test",
        vocs=vocs,
        generator=generator,
        environment={"name": "test"},
        initial_points=pd.DataFrame(test_routine["init_points"]),
        critical_constraint_names=["c"],
    )


def create_routine_constrained_ucb() -> Routine:

    test_routine: dict[str, Any] = {
        "name": "routine-for-ucb-cons-test",
        "generator": "expected_improvement",
        "env": "test",
        "generator_params": {
            "turbo_controller": "optimize",
            "gp_constructor": {
                "name": "standard",
                "use_low_noise_prior": True,
            },
            "beta": 2.0,
        },
        "env_params": {},
        "vocs": {
            "variables": {"x0": [-1, 1], "x1": [-1, 1], "x2": [-1, 1], "x3": [-1, 1]},
            "objectives": {"f": "MAXIMIZE"},
            "constraints": {"c": ["GREATER_THAN", 0]},
        },
        "init_points": {"x0": [0.5], "x1": [0.5], "x2": [0.5], "x3": [0.5]},
    }

    vocs = VOCS(**test_routine["vocs"])

    generator = UpperConfidenceBoundGenerator(
        vocs=vocs, **test_routine["generator_params"]
    )

    return Routine(
        name="test",
        vocs=vocs,
        generator=generator,
        environment={"name": "test"},
        initial_points=pd.DataFrame(test_routine["init_points"]),
    )


def get_current_vars(routine: Routine) -> list[float]:
    var_names = routine.vocs.variable_names
    var_dict = routine.environment.get_variables(var_names)

    return list(var_dict.values())


def get_vars_in_row(routine: Routine, idx: int = 0) -> np.ndarray:
    var_names = routine.vocs.variable_names
    if routine.data is None:
        raise ValueError("Routine data is None. Unable to get variables in row.")
    output = routine.data.iloc[idx][var_names].to_numpy()
    # output = routine.data.iat[idx][var_names].to_numpy()
    return output


def fix_path_issues() -> None:
    from badger.settings import init_settings
    from badger.archive import BADGER_ARCHIVE_ROOT

    config_singleton = init_settings()
    BADGER_TEMPLATE_ROOT = config_singleton.read_value("BADGER_TEMPLATE_ROOT")

    os.makedirs(BADGER_ARCHIVE_ROOT, exist_ok=True)
    os.makedirs(BADGER_TEMPLATE_ROOT, exist_ok=True)
