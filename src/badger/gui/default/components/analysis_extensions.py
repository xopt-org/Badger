from typing import Optional, cast
import logging

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDialog, QVBoxLayout
from PyQt5.QtGui import QCloseEvent
from badger.gui.default.components.analysis_widget import AnalysisWidget
from badger.gui.default.components.bo_visualizer.bo_widget import BOPlotWidget
from badger.gui.default.components.pf_viewer.pf_widget import ParetoFrontWidget
from badger.routine import Routine

from xopt.generators.bayesian.bayesian_generator import BayesianGenerator
from xopt.generators.bayesian.mobo import MOBOGenerator
from xopt import Generator

logger = logging.getLogger(__name__)


class AnalysisExtension(QDialog):
    window_closed = pyqtSignal(object)
    generator_type = Generator
    widget = AnalysisWidget

    def __init__(self, parent: Optional[QDialog] = None):
        super().__init__(parent=parent)

    def update_window(self, routine: Routine) -> None:
        try:
            self.update_extension(routine)
        except Exception as e:
            # This will make sure that the extension window closes if an error occurs
            self.close()
            raise e

    def initialize_extension(
        self,
        extension_widget: AnalysisWidget,
        extension_name: str,
        generator_type: type[Generator],
    ) -> None:
        logger.debug(f"Initializing {extension_name} Extension")

        self.setWindowTitle(extension_name)

        self.generator_type = generator_type

        self.widget = extension_widget
        self.widget.update_extension = self.update_extension

        bo_layout = QVBoxLayout()
        bo_layout.addWidget(self.widget)
        self.setLayout(bo_layout)

    def update_extension(
        self, routine: Routine, requires_rebuild: bool = False
    ) -> None:
        """
        Update the extension with the new routine.
        This method should be implemented to handle the update logic for the extension.
        """

        self.widget = cast(AnalysisWidget, self.widget)

        self.widget.isValidRoutine(routine)

        self.widget.update_routine(routine, self.generator_type)

        if self.widget.requires_reinitialization():
            self.widget.initialize_widget()

        self.widget.update_plots(requires_rebuild, interval=self.widget.update_interval)

    def closeEvent(self, a0: Optional[QCloseEvent]) -> None:
        self.window_closed.emit(self)
        super().closeEvent(a0)


class ParetoFrontViewer(AnalysisExtension):
    def __init__(self):
        super().__init__()

        self.initialize_extension(
            extension_widget=ParetoFrontWidget(),
            extension_name="Pareto Front Viewer",
            generator_type=MOBOGenerator,
        )


class BOVisualizer(AnalysisExtension):
    def __init__(self):
        super().__init__()

        self.initialize_extension(
            extension_widget=BOPlotWidget(),
            extension_name="Bayesian Optimization Visualizer",
            generator_type=BayesianGenerator,
        )
