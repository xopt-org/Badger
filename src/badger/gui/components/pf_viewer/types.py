"""TypedDict definitions for the Pareto front viewer — plot options and
objective/variable selection."""

from typing import TypedDict

from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
)

from badger.gui.components.types import InteractionParameters


class PlotOptions(TypedDict):
    show_only_pareto_front: bool


class ConfigurableOptions(InteractionParameters):
    plot_options: PlotOptions
    objectives: list[str]
    objective_1: int
    objective_2: int
    plot_tab: int


class PFOptionsUIWidgets(TypedDict):
    show_only_pareto_front: QCheckBox


class PFVariablesUIWidgets(TypedDict):
    variable_1: QComboBox
    variable_2: QComboBox


class PFPlotUIWidgets(TypedDict):
    pareto: QTabWidget
    hypervolume: QVBoxLayout


class PFUIWidgets(TypedDict):
    variables: PFVariablesUIWidgets
    options: PFOptionsUIWidgets
    update: QPushButton
    plot: PFPlotUIWidgets


class PFVariablesLayouts(TypedDict):
    variable_1: QVBoxLayout
    variable_2: QVBoxLayout


class PFUILayouts(TypedDict):
    main: QHBoxLayout
    settings: QVBoxLayout
    plot: QGridLayout
    options: QVBoxLayout
    variables: QVBoxLayout
    update: QVBoxLayout


class PFUI(TypedDict):
    components: PFUIWidgets
    layouts: PFUILayouts
