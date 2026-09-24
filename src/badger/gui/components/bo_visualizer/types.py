"""TypedDict definitions for BO visualizer options — grid resolution,
display toggles, variable selection, and reference points."""

from typing import TypedDict

from badger.gui.components.types import InteractionParameters


class PlotOptions(TypedDict):
    n_grid: int
    n_grid_range: tuple[int, int]
    show_samples: bool
    show_prior_mean: bool
    show_feasibility: bool
    show_acq_func: bool


class ConfigurableOptions(InteractionParameters):
    plot_options: PlotOptions
    include_variable_2: bool
