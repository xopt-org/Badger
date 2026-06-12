from enum import StrEnum
from typing import NamedTuple


class Solution(NamedTuple):
    variables: list[float]
    objectives: list[float]
    constraints: list[float]
    states: list[float]
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
