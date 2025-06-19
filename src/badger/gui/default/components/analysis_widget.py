from abc import abstractmethod
from typing import Optional

from PyQt5.QtWidgets import QDialog, QMessageBox
from badger.routine import Routine
from xopt import Generator

import logging


logger = logging.getLogger(__name__)


class AnalysisWidget(QDialog):
    routine: Routine
    generator = None
    parameters = None
    df_length: float = float("inf")
    initialized: bool = False
    routine_identifier: str = ""
    last_updated: float = -float("inf")
    update_interval: int = 1000  # Default update interval in milliseconds

    def __init__(self, parent: Optional[QDialog] = None):
        super().__init__(parent=parent)

    @abstractmethod
    def requires_reinitialization(self) -> bool:
        """
        Check if the widget requires reinitialization.
        This is used to determine if the widget needs to be reset or updated.
        """
        pass

    @abstractmethod
    def update_plots(self, requires_rebuild: bool, interval: int) -> None:
        """
        Update the plots in the widget.
        This method should be implemented to update the visualizations based on the current data.
        """
        pass

    @abstractmethod
    def setup_connections(self) -> None:
        """
        Set up the connections for the widget.
        This method should be implemented to connect signals and slots for the widget.
        """
        pass

    @abstractmethod
    def isValidRoutine(self, routine: Routine) -> bool:
        """
        Check if the routine is valid for this widget.
        This method should be implemented to validate the routine before updating the widget.
        """
        pass

    def update_routine(self, routine: Routine, generator_type: type[Generator]) -> None:
        logger.debug("Updating routine in Pareto Front Viewer")

        self.routine = routine

        # Check if the generator is a BayesianGenerator
        if not issubclass(self.routine.generator.__class__, generator_type):
            QMessageBox.critical(
                self,
                "Invalid Generator",
                f"Invalid generator type: {type(self.routine.generator)}, extension only supports {generator_type.__name__}",
            )
            raise TypeError(
                f"Invalid generator type: {type(self.routine.generator)}, extension only supports {generator_type.__name__}"
            )

        if self.routine.generator.data is None:
            logger.error("No data available in generator")
            return

        self.df_length = len(self.routine.generator.data)
        self.generator = self.routine.generator
