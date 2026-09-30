from __future__ import annotations

from dataclasses import dataclass
from multiprocessing import Process, Queue
from multiprocessing.connection import Connection
from multiprocessing.synchronize import Event
from typing import Any

import pandas as pd

from badger.errors import (
    MEASUREMENT_ACTION_TYPE,
    MEASUREMENT_ERROR_TYPE,
    ROUTINE_ERROR_TYPE,
    TERMINATION_ACTION_TYPE,
    TERMINATION_REACHED_TYPE,
)


@dataclass
class MeasurementErrorMessage:
    """Subprocess -> routine runner: an environment measurement raised.

    Prompts the user to retry or abort the run.
    """

    title: str
    traceback: str
    type: str = MEASUREMENT_ERROR_TYPE


@dataclass
class TerminationReachedMessage:
    """Subprocess -> routine runner: a run-until condition was reached.

    Prompts the user to continue or end the run. ``tc_condition`` is a flat
    dict with keys ``type``, ``config`` and ``state``.
    """

    tc_condition: dict[str, Any]
    title: str = "Termination condition reached"
    type: str = TERMINATION_REACHED_TYPE


@dataclass
class RoutineErrorMessage:
    """Subprocess -> routine runner: a fatal error ended the run.

    Shown to the user in an error dialog.
    """

    title: str
    traceback: str
    type: str = ROUTINE_ERROR_TYPE


# Messages carried by the data/error queue from the subprocess to the runner.
DataQueueMessage = (
    MeasurementErrorMessage | TerminationReachedMessage | RoutineErrorMessage
)


@dataclass
class MeasurementActionMessage:
    """Routine runner -> subprocess: user's response to a measurement error.

    ``action`` is ``MEASUREMENT_ACTION_RETRY`` or ``MEASUREMENT_ACTION_ABORT``.
    """

    action: str
    type: str = MEASUREMENT_ACTION_TYPE


@dataclass
class TerminationActionMessage:
    """Routine runner -> subprocess: user's response to a termination prompt.

    ``action`` is ``TERMINATION_ACTION_CONTINUE`` or ``TERMINATION_ACTION_END``.
    """

    action: str
    type: str = TERMINATION_ACTION_TYPE


# Messages carried by the dialog action queue from the runner to the subprocess.
DialogActionMessage = MeasurementActionMessage | TerminationActionMessage


@dataclass
class TerminationConditionConfig:
    """Run-until configuration set in the termination condition dialog.

    ``tc_idx`` selects which limit is active: 0 = max evaluations (``max_eval``),
    1 = max running time in seconds (``max_time``). ``ftol`` is reserved for a
    convergence-tolerance mode that is not yet wired up.
    """

    tc_idx: int = 0
    max_eval: int = 0
    max_time: float = 0.0
    ftol: float = 0.0


@dataclass
class ArgumentQueueType:
    routine_id: str
    routine_filename: str
    routine_name: str
    variable_ranges: dict[str, Any]
    initial_points: pd.DataFrame | None
    evaluate: bool
    archive: bool
    termination_condition: TerminationConditionConfig | None
    start_time: float
    testing: bool
    run_data: bool
    init_points: bool


@dataclass
class ProcessWithArgs:
    process: Process
    stop_event: Event
    pause_event: Event
    args_queue: Queue[ArgumentQueueType]
    data_queue: Queue[DataQueueMessage]
    evaluate_queue: tuple[Connection, Connection]
    wait_event: Event
    dialog_action_queue: Queue[DialogActionMessage]
