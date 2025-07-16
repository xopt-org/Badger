from abc import abstractmethod
from collections.abc import Callable
from typing import Optional

from PyQt5.QtWidgets import QDialog
from badger.gui.default.components.extension_utilities import HandledException
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
    update_extension: Callable[[Routine, bool], None]

    def __init__(
        self,
        parent: Optional[QDialog] = None,
    ):
        super().__init__(parent=parent)

    @abstractmethod
    def initialize_widget(self) -> None:
        """
        Initialize the widget.
        This method should be implemented to set up the initial state of the widget.
        """
        pass

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
    def isValidRoutine(self, routine: Routine) -> None:
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
            raise HandledException(
                TypeError,
                f"Invalid generator type: {type(self.routine.generator)}, extension only supports {generator_type.__name__}",
            )

        if self.routine.generator.data is None:
            logger.error(
                "No data available in generator, will try to get data from routine"
            )
            if self.routine.data is None:
                raise HandledException(
                    ValueError, "No data available in generator or routine"
                )
            self.routine.generator.data = self.routine.data

        self.df_length = len(self.routine.generator.data)
        self.generator = self.routine.generator
