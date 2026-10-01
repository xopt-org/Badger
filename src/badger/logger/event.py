"""Event constants (start, step, end) that the optimization loop fires
to notify loggers and observers of progress."""

from enum import StrEnum
from typing import NamedTuple


class Solution(NamedTuple):
    variables: list[float] | None
    objectives: list[float] | None
    constraints: list[float] | None
    states: list[float] | None
    is_optimal: bool
    variable_names: list[str]
    objective_names: list[str]
    constraint_names: list[str]
    observable_names: list[str]


class Events(StrEnum):
    OPTIMIZATION_START = "optimization:start"
    OPTIMIZATION_STEP = "optimization:step"
    OPTIMIZATION_END = "optimization:end"


DEFAULT_EVENTS = [
    Events.OPTIMIZATION_START,
    Events.OPTIMIZATION_STEP,
    Events.OPTIMIZATION_END,
]
