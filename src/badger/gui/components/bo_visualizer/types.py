from typing import TypedDict


class PlotOptions(TypedDict):
    n_grid: int
    n_grid_range: tuple[int, int]
    show_samples: bool
    show_prior_mean: bool
    show_feasibility: bool
    show_acq_func: bool


class ConfigurableOptions(TypedDict):
    plot_options: PlotOptions
    variable_1: int
    variable_2: int
    variables: list[str]
    reference_points: dict[str, float]
    reference_points_range: dict[str, tuple[float, float]]
    include_variable_2: bool
