"""UI layout definitions for the BAX visualizer widget."""

from typing import TYPE_CHECKING

from badger.gui.components.bax_visualizer.controls import ControlsWidget
from badger.gui.components.extension_utilities import (
    get_latest_reference_points,
)

if TYPE_CHECKING:
    from badger.gui.components.bax_visualizer.bax_widget import Parameters

from PyQt5.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from badger.gui.components.bax_visualizer.plotting import PlottingWidget
from badger.routine import Routine


class UI(QWidget):
    def __init__(
        self,
        routine: Routine,
        parameters: "Parameters",
        parent: QWidget | None = None,
    ):
        super().__init__(parent=parent)

        self.routine = routine
        self.parameters = parameters
        self.initialize_ui()

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(1250, 600)

    def initialize_ui(self) -> None:
        main_layout = QHBoxLayout()

        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        controls_layout = QVBoxLayout()

        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(0)

        self.controls_area = ControlsWidget(
            routine=self.routine, parameters=self.parameters
        )

        self.controls_area.setSizePolicy(
            QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding
        )
        self.controls_area.setMinimumWidth(250)

        controls_layout.addWidget(self.controls_area, stretch=0)

        main_layout.addLayout(controls_layout)

        self.plotting_area = PlottingWidget(
            generator=self.routine.generator,
            parameters=self.parameters,
        )

        main_layout.addWidget(self.plotting_area, stretch=1)

        self.setLayout(main_layout)

    def set_parameters(self, parameters: "Parameters") -> None:
        """Point this widget and every child widget at the same parameters object.

        This must be called whenever the top-level parameters object is
        replaced (e.g. on reinitialization) so the controls and plotting areas
        do not keep reading/writing a stale object from a previous run.
        """
        self.parameters = parameters
        self.controls_area.parameters = parameters
        self.plotting_area.parameters = parameters

    def set_routine(self, routine: Routine) -> None:
        """Point this widget and every child widget at the current routine.

        The child widgets cache the routine (and its generator) they were built
        with. When the user switches routines, those caches must be refreshed or
        the controls/reference table will read the previous run's variables and
        data (e.g. leftover reference-point keys that no longer exist in the new
        routine's vocs).
        """
        self.routine = routine
        self.controls_area.routine = routine
        self.plotting_area.generator = routine.generator

    def reset_ui(self) -> None:
        """Reset the UI to its initial state."""
        self.controls_area.reset_controls_widget()
        self.controls_area.update_controls()

    def initialize_reference_table(self) -> None:
        """Initialize the reference table in the controls area."""

        reference_points = get_latest_reference_points(
            self.routine.generator.data, self.parameters.variables
        )

        self.parameters.tab_1.reference_points = reference_points

        self.controls_area.populate_reference_table()
