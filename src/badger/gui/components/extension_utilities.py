import time
from functools import wraps
import traceback
from typing import Any, Callable, Optional, Iterable, ParamSpec
from types import TracebackType
from PyQt5.QtWidgets import QWidget, QLayout, QTabWidget

from matplotlib.axes import Axes
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

import logging

logger = logging.getLogger(__name__)

Param = ParamSpec("Param")


def signal_logger(
    text: str,
) -> Callable[[Callable[Param, None]], Callable[Param, None]]:
    def decorator(fn: Callable[Param, None]) -> Callable[Param, None]:
        @wraps(fn)
        def wrapper(*args: Param.args, **kwargs: Param.kwargs) -> None:
            logger.debug(f"{text}")
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def clear_layout(layout: QLayout) -> None:
    while layout.count() > 0:
        child = layout.takeAt(0)
        if child is None:
            break

        widget = child.widget()
        if widget is None:
            raise HandledException(
                ValueError, "Child of layout is not a widget. Cannot clear layout."
            )

        widget.deleteLater()


def clear_tabs(tab_widget: QTabWidget) -> None:
    max_index = tab_widget.count()
    for i in range(max_index - 1, -1, -1):
        tab_widget.removeTab(i)


def requires_update(
    last_updated: Optional[float], interval: int = 1000, requires_rebuild: bool = False
) -> bool:
    # Check if the plot was updated recently
    if last_updated is not None and not requires_rebuild:
        logger.debug(f"Time since last update: {time.time() - last_updated}")

        time_diff = time.time() - last_updated

        # If the plot was updated less than 1 second ago, skip this update
        if time_diff < interval / 1000:
            logger.debug("Skipping update")
            return False
    return True


def to_precision_float(value: Any, precision: int = 4) -> float:
    try:
        return float(f"{value:.{precision}g}")
    except Exception:
        raise HandledException(
            ValueError,
            f"Value {value} cannot be converted to float with precision {precision}",
        )


class HandledException(Exception):
    """
    Custom exception class to handle exceptions in a way that can be caught and logged.
    This is useful for handling exceptions in contexts where we want to log them without
    interrupting the flow of the program.
    """

    def __init__(
        self, exception_type: type[BaseException], message: str, *args: object
    ) -> None:
        super().__init__(message, *args)
        self.message = message
        self.exception_type = exception_type
        self.traceback = traceback.format_exc()

        logger.error(
            f"HandledException raised: {self.exception_type.__name__}: {self.message}\n\n{self.traceback}"
        )

    def __str__(self) -> str:
        return f"{self.exception_type.__name__}: {self.message}"


class BlockSignalsContext:
    widgets: Iterable[QWidget | QLayout]

    def __init__(self, widgets: QWidget | QLayout | Iterable[QWidget | QLayout]):
        if isinstance(widgets, Iterable):
            self.widgets = widgets
        else:
            self.widgets = [widgets]

    def __enter__(self):
        for widget in self.widgets:
            if widget.signalsBlocked():
                logger.warning(
                    f"Signals already blocked for {widget} when entering context. Nesting BlockSignalsContext is not recommended as blockSignals is set to False upon exiting the context. This may lead to unexpected behavior if the widget is used again from within another BlockSignalsContext."
                )
            widget.blockSignals(True)

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        exc_traceback: Optional[TracebackType],
    ):
        for widget in self.widgets:
            if not widget.signalsBlocked():
                logger.warning(
                    f"Signals not blocked for {widget} when exiting context. Nesting BlockSignalsContext is not recommended as blockSignals is set to False upon exiting the context. This may lead to unexpected behavior if the widget is used again from within another BlockSignalsContext."
                )
            widget.blockSignals(False)


class MatplotlibFigureContext:
    def __init__(
        self,
        fig: Figure | None = None,
        ax: Axes | None = None,
        fig_size: tuple[float, float] | None = None,
    ):
        self.fig_size = fig_size
        if fig is None:
            self.fig = Figure(figsize=self.fig_size, tight_layout=True)
        else:
            self.fig = fig
            self.fig.set_layout_engine("tight")
            if self.fig_size is not None:
                self.fig.set_size_inches(*self.fig_size)

        if ax is None:
            self.ax = self.fig.add_subplot()
        else:
            self.ax = ax

    def __enter__(self):
        return self.fig, self.ax

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        exc_traceback: Optional[TracebackType],
    ):
        plt.close(self.fig)
