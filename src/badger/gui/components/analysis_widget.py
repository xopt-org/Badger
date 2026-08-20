"""Base class that all analysis extension widgets must implement.
Defines the interface for receiving routine updates and rendering plots."""

import logging
from abc import abstractmethod
from collections.abc import Callable
from typing import Any

from PyQt5.QtWidgets import QWidget
from xopt import Generator

from badger.gui.components.extension_utilities import HandledException
from badger.routine import Routine
from badger.utils import create_archive_run_filename

logger = logging.getLogger(__name__)


class AnalysisWidget(QWidget):
    routine: Routine
    generator: Generator
    parameters: dict[str, Any] = {}
    df_length: float = float("inf")
    initialized: bool = False
    routine_identifier: str = ""
    last_updated: float = -float("inf")
    update_interval: int = 1000  # Default update interval in milliseconds
    update_extension: Callable[[Routine, bool], None]

    def __init__(
        self,
        routine: Routine,
        parent: QWidget | None = None,
    ):
        super().__init__(parent=parent)
        self.routine = routine
        self.generator = routine.generator

    @abstractmethod
    def initialize_widget(self) -> None:
        """
        Initialize the widget.
        This method should be implemented to set up the initial state of the widget.
        """
        raise NotImplementedError("initialize_widget method not implemented")

    @abstractmethod
    def update_plots(self, requires_rebuild: bool, interval: int) -> None:
        """
        Update the plots in the widget.
        This method should be implemented to update the visualizations based on the current data.
        """
        raise NotImplementedError("update_plots method not implemented")

    @abstractmethod
    def setup_connections(self) -> None:
        """
        Set up the connections for the widget.
        This method should be implemented to connect signals and slots for the widget.
        """
        raise NotImplementedError("setup_connections method not implemented")

    @abstractmethod
    def isValidRoutine(self, routine: Routine) -> None:
        """
        Check if the routine is valid for this widget.
        This method should be implemented to validate the routine before updating the widget.
        """
        raise NotImplementedError("isValidRoutine method not implemented")

    @abstractmethod
    def reset_widget(self) -> None:
        """
        Reset the widget to its initial state.
        This method should be implemented to clear the current state and prepare the widget for a new routine.
        """
        raise NotImplementedError("reset_widget method not implemented")

    def requires_reinitialization(self) -> bool:
        # Check if the extension needs to be reinitialized
        logger.debug("Checking if AnalysisWidget needs to be reinitialized")

        archive_name = create_archive_run_filename(self.routine)

        logger.debug(f"Archive name: {archive_name}")

        if not self.initialized:
            logger.debug("Reset - Extension never initialized")
            # Set up connections
            logger.debug("Setting up connections")
            self.setup_connections()
            self.routine_identifier = archive_name
            self.initialized = True
            # Track the current data length so the growth check does not treat
            # the first post-init update as a shrink and reinitialize again.
            if self.routine.data is not None:
                self.df_length = len(self.routine.data)
            return True

        if self.routine_identifier != archive_name:
            logger.debug("Reset - Routine name has changed")
            # Reset first: reset_widget() clears routine_identifier, so the new
            # identifier must be assigned afterwards. Assigning before the reset
            # would be clobbered back to "" and force a reinitialization on every
            # subsequent update during the same run.
            self.reset_widget()
            self.routine_identifier = archive_name
            # Sync the tracked data length to the new routine so the growth
            # check below does not immediately treat the next update as a
            # shrink (df_length is left at inf by reset_widget()).
            if self.routine.data is not None:
                self.df_length = len(self.routine.data)
            return True

        if self.routine.data is None:
            logger.debug("Reset - No data available")

            return True

        previous_len = self.df_length
        self.df_length = len(self.routine.data)
        new_length = self.df_length

        if previous_len > new_length:
            logger.debug("Reset - Data length is smaller")
            # Keep df_length at the current (smaller) length rather than resetting
            # it to inf. Leaving it at inf would make every subsequent update look
            # like a shrink and reinitialize the widget on a loop.
            return True

        return False

    def update_routine(self, routine: Routine, generator_type: type[Generator]) -> None:
        self.routine = routine

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
