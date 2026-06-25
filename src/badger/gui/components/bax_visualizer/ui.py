"""UI layout definitions for the BAX visualizer widget."""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from badger.gui.components.bax_visualizer.bax_widget import Parameters

from PyQt5.QtWidgets import QVBoxLayout, QWidget

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

    def _initialize_ui(self) -> None:
        main_layout = QVBoxLayout()
        controls_layout = QVBoxLayout()

        main_layout.addLayout(controls_layout)

        self.plotting_area = PlottingWidget(
            generator=self.routine.generator, parameters=self.parameters
        )

        main_layout.addWidget(self.plotting_area)

        self.setLayout(main_layout)
