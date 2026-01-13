from typing import TypedDict


class ConfigurableOptions(TypedDict, total=False):
    variable_1: int
    variable_2: int
    variables: list[str]
    reference_points: dict[str, float]
    reference_points_range: dict[str, tuple[float, float]]
    include_variable_2: bool
    plot_options: dict[str, bool | int]
