"""UI layout definitions for the BAX visualizer widget."""

from typing import TYPE_CHECKING, Optional

from badger.gui.components.bax_visualizer.controls import ControlsWidget
from badger.gui.components.extension_utilities import to_precision_float

if TYPE_CHECKING:
    from badger.gui.components.bax_visualizer.bax_widget import Parameters

from gest_api.vocs import ContinuousVariable
from PyQt5.QtWidgets import QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

from badger.gui.components.bax_visualizer.plotting import PlottingWidget
from badger.routine import Routine


class UI(QWidget):
    def __init__(
        self,
        routine: Routine,
        parameters: "Parameters",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent=parent)

        self.routine = routine
        self.parameters = parameters
        self._initialize_ui()

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(1250, 600)

    def _initialize_ui(self) -> None:
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

    def initialize_reference_table(self) -> None:
        """Initialize the reference table in the controls area."""

        reference_points: dict[str, float] = {}

        vocs_variables = self.routine.vocs.variables

        for var_name, variable in vocs_variables.items():
            if not isinstance(variable, ContinuousVariable):
                raise ValueError(
                    f"Variable '{var_name}' is not continuous. Only continuous variables are supported for reference points."
                )

            domain_range = variable.domain[1] - variable.domain[0]

            reference_points[var_name] = to_precision_float(
                variable.domain[0] + (domain_range / 2.0)
            )

        self.parameters.tab_1.reference_points = reference_points

        self.controls_area.populate_reference_table()
