"""TypedDict definitions for the Pareto front viewer — plot options and
objective/variable selection."""

from typing import TypedDict


class PlotOptions(TypedDict):
    show_only_pareto_front: bool


class ConfigurableOptions(TypedDict):
    plot_options: PlotOptions
    variable_1: int
    variable_2: int
    variables: list[str]
    objectives: list[str]
    objective_1: int
    objective_2: int
    plot_tab: int
