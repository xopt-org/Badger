from __future__ import annotations

from dataclasses import dataclass
from multiprocessing import Process, Queue
from multiprocessing.connection import Connection
from multiprocessing.synchronize import Event
from typing import Any

import pandas as pd


@dataclass
class ArgumentQueueType:
    routine_id: str
    routine_filename: str
    routine_name: str
    variable_ranges: dict[str, Any]
    initial_points: pd.DataFrame | None
    evaluate: bool
    archive: bool
    termination_condition: dict[str, Any] | None
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
    data_queue: Queue[dict[str, Any] | tuple[str, str]]
    evaluate_queue: tuple[Connection, Connection]
    wait_event: Event
    dialog_action_queue: Queue[dict[str, str]]
