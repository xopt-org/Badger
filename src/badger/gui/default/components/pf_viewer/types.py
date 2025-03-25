from typing import TypedDict
from PyQt5.QtWidgets import (
    QRadioButton,
    QComboBox,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
)


class PlotOptions(TypedDict):
    show_samples: bool
    show_prior_mean: bool
    show_feasibility: bool
    show_acq_func: bool


class ConfigurableOptions(TypedDict):
    plot_options: PlotOptions
    variable_1: int
    variable_2: int


class PFOptionsUIWidgets(TypedDict):
    sample_checkbox: QRadioButton


class PFVariablesUIWidgets(TypedDict):
    variable_1: QComboBox
    variable_2: QComboBox


class PFUIWidgets(TypedDict):
    variables: PFVariablesUIWidgets
    options: PFOptionsUIWidgets
    update: QRadioButton
    plot: QTabWidget


class PFVariablesLayouts(TypedDict):
    variable_1: QVBoxLayout
    variable_2: QVBoxLayout


class PFUILayouts(TypedDict):
    main: QHBoxLayout
    settings: QVBoxLayout
    plot: QVBoxLayout
    options: QVBoxLayout
    variables: QVBoxLayout
    update: QVBoxLayout


class PFUI(TypedDict):
    components: PFUIWidgets
    layouts: PFUILayouts
