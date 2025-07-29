from badger.routine import Routine
from matplotlib.backend_bases import MouseEvent, MouseButton, PickEvent
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from badger.gui.default.components.types import ConfigurableOptions
from badger.gui.default.components.extension_utilities import (
    HandledException,
    to_precision_float,
)

from typing import cast

import logging

from matplotlib.collections import PathCollection
from matplotlib.text import Annotation
from pyparsing import Callable

logger = logging.getLogger(__name__)


class MatplotlibInteractionHandler:
    """
    Handles matplotlib interaction events such as clicks, mouse movements, and scrolls.
    This class is designed to be used with matplotlib figures and axes.
    """

    parameters: ConfigurableOptions
    routine: Routine
    callback: Callable[[Routine, bool], None]
    moving: bool
    start: dict[str, float]  # Starting coordinates for movement

    def __init__(
        self,
        canvas: FigureCanvasQTAgg,
        parameters: ConfigurableOptions,
        routine: Routine,
        callback: Callable[[Routine, bool], None],
    ):
        self.canvas = canvas
        self.parameters = parameters
        self.routine = routine
        self.callback = callback
        self.moving = False
        self.start = {"x": 0, "y": 0}  # Starting coordinates for movement
        self.step = 0
        self.tooltips: list[Annotation] = []

    def connect_events(self) -> None:
        self.canvas.mpl_connect(
            "button_press_event",
            lambda event: self.on_click(
                event,  # type: ignore[call-arg]
                self.parameters,
                self.routine,
                self.callback,
            ),
        )
        # self.canvas.mpl_connect(
        #     "button_release_event",
        #     lambda event: self.on_release(
        #         event,  # type: ignore[call-arg]
        #     ),
        # )
        # self.canvas.mpl_connect(
        #     "motion_notify_event",
        #     lambda event: self.on_motion(event),  # type: ignore[call-arg]
        # )

        self.canvas.mpl_connect(
            "scroll_event",
            lambda event: self.on_scroll(event),  # type: ignore[call-arg]
        )

        self.canvas.mpl_connect(
            "pick_event",
            lambda event: self.on_pick(event),  # type: ignore[call-arg]
        )

    def update_reference_points(
        self,
        parameters: ConfigurableOptions,
        desired_coordinate: tuple[float, float],
    ) -> None:
        if (
            "variable_1" not in parameters
            or "variable_2" not in parameters
            or "variables" not in parameters
        ):
            raise HandledException(
                ValueError,
                "Variables 'variable_1' or 'variable_2' or 'variables' are not found in parameters.",
            )
        variable_1 = parameters["variable_1"]
        variable_2 = parameters["variable_2"]

        variable_1_name = parameters["variables"][variable_1]
        variable_2_name = parameters["variables"][variable_2]

        if "reference_points" not in parameters:
            raise ValueError(
                "Reference points not found in parameters. "
                "Please ensure 'reference_points' is initialized."
            )

        logger.debug(f"Updated reference points: {parameters['reference_points']}")

        parameters["reference_points"][variable_1_name] = to_precision_float(
            desired_coordinate[0]
        )
        parameters["reference_points"][variable_2_name] = to_precision_float(
            desired_coordinate[1]
        )

        logger.debug(f"Updated reference points: {parameters['reference_points']}")

    def on_click(
        self,
        event: MouseEvent,
        parameters: ConfigurableOptions,
        routine: Routine,
        callback: Callable[[Routine, bool], None],
    ) -> None:
        logger.debug(f"Clicked at {event.xdata}, {event.ydata}, button: {event.button}")
        if event.inaxes is None:
            logger.debug("Click outside axes, ignoring")
            return

        if event.xdata is None or event.ydata is None:
            logger.debug("Click coordinates are None, ignoring")
            return

        axis = event.inaxes
        logger.debug(f"Click in axes: {axis.get_title()}")
        clicked = False
        if event.button == MouseButton.MIDDLE:
            logger.debug("Middle click detected")
            # Reset reference points back to the initial values

            if "reference_points_range" in parameters:
                initial_reference_points = parameters["reference_points_range"]
                parameters["reference_points"] = {
                    key: (
                        initial_reference_points[key][0]
                        + initial_reference_points[key][1]
                    )
                    / 2
                    for key in initial_reference_points
                }
            clicked = True
        elif event.button == MouseButton.RIGHT:
            logger.debug("Right click detected")

            if "reference_points" in parameters:
                coordinate: tuple[float, float] = (event.xdata, event.ydata)
                self.update_reference_points(
                    parameters,
                    coordinate,
                )
            clicked = True
        # elif event.button == MouseButton.LEFT:
        #     self.start["x"] = event.xdata
        #     self.start["y"] = event.ydata
        #     self.moving = True

        if clicked:
            callback(routine, True)

    def on_motion(self, event: MouseEvent) -> None:
        if event.inaxes is None:
            return

        axis = event.inaxes

        if not self.moving:
            logger.debug("Mouse is not moving, ignoring motion event")
            return

        if event.xdata is None or event.ydata is None:
            logger.debug("Mouse coordinates are None, ignoring")
            return

        current_x_range = axis.get_xlim()
        current_y_range = axis.get_ylim()

        x_range = current_x_range[1] - current_x_range[0]
        y_range = current_y_range[1] - current_y_range[0]

        movement_x = event.xdata - self.start["x"]
        movement_y = event.ydata - self.start["y"]

        new_x_range = (
            current_x_range[0] - movement_x,
            current_x_range[0] + x_range - movement_x,
        )
        new_y_range = (
            current_y_range[0] - movement_y,
            current_y_range[0] + y_range - movement_y,
        )

        axis.set_xlim(new_x_range)
        axis.set_ylim(new_y_range)

        event.canvas.draw_idle()

    def on_release(self, event: MouseEvent) -> None:
        logger.debug(
            f"Mouse released at {event.xdata}, {event.ydata}, button: {event.button}"
        )
        if event.button == MouseButton.LEFT:
            self.moving = False
            logger.debug("Mouse left button released, stopping movement")
        else:
            logger.debug("Mouse button released, no action taken")

    def on_scroll(self, event: MouseEvent) -> None:
        logger.debug(f"Mouse scrolled step: {event.step}")
        if event.inaxes is None:
            logger.debug("Mouse moved outside axes, ignoring")
            return

        # Filter out excessive scroll events by ignoring if the step is too large
        MAX_STEP = 3
        if abs(event.step) > MAX_STEP:
            logger.debug(f"Ignoring excessive scroll event with step: {event.step}")
            return

        axis = event.inaxes

        current_x_range = axis.get_xlim()
        current_y_range = axis.get_ylim()

        x_range = current_x_range[1] - current_x_range[0]
        y_range = current_y_range[1] - current_y_range[0]

        SCALE_FACTOR = 0.1

        if event.step < 0:
            axis.set_xlim(
                current_x_range[0] - x_range * SCALE_FACTOR,
                current_x_range[1] + x_range * SCALE_FACTOR,
            )
            axis.set_ylim(
                current_y_range[0] - y_range * SCALE_FACTOR,
                current_y_range[1] + y_range * SCALE_FACTOR,
            )
        elif event.step > 0:
            axis.set_xlim(
                current_x_range[0] + x_range * SCALE_FACTOR,
                current_x_range[1] - x_range * SCALE_FACTOR,
            )
            axis.set_ylim(
                current_y_range[0] + y_range * SCALE_FACTOR,
                current_y_range[1] - y_range * SCALE_FACTOR,
            )

        event.canvas.draw_idle()

    def on_pick(self, event: PickEvent) -> None:
        logger.debug("on_pick event triggered")
        plot = event.artist
        mouseevent = event.mouseevent
        if mouseevent.inaxes is None:
            logger.debug("Mouse event outside axes, ignoring")
            return

        ax = mouseevent.inaxes

        click_location_x = mouseevent.x
        click_location_y = mouseevent.y

        figure_dimensions = event.canvas.get_width_height()

        self.region = (
            1 if (figure_dimensions[0] / 2 > click_location_x) else -1,
            1 if (figure_dimensions[1] / 2 > click_location_y) else -1,
        )

        if isinstance(plot, PathCollection):
            data = plot.get_offsets()

            indexes = cast(list[int], event.ind)

            if len(indexes) == 0:
                logger.debug("No indices in pick event, ignoring")
                return
            index = indexes[0]

            if index < 0 or index >= len(data):
                logger.debug(f"Index {index} out of bounds for data length {len(data)}")
                return

            point = cast(tuple[float, float], data[index])
            logger.debug(f"Picked point: {point} at index {index}")

            # Routine data
            routine_data = self.routine.generator.data

            if routine_data is None:
                logger.error("No routine data available.")
                return

            x_column = ax.get_xlabel()
            y_column = ax.get_ylabel()

            if x_column not in routine_data or y_column not in routine_data:
                logger.error(
                    f"Columns {x_column} or {y_column} not found in routine data."
                )

            # Find the true index in the routine data
            # This is done by finding the row in the routine data that is closest to the picked point
            true_index = routine_data.loc[  # type: ignore
                (routine_data[x_column] - point[0]).abs().idxmin()  # type: ignore
                & (routine_data[y_column] - point[1]).abs().idxmin()
            ].name

            if true_index is None:
                logger.error("True index not found in routine data.")
                true_index = "Index not found"

            # Create tooltip text
            tooltip_text = f"Index: {true_index}\n({to_precision_float(point[0])}, {to_precision_float(point[1])})"

            self.clear_tooltips()  # Clear existing tooltips before adding a new one

            # Create and add the tooltip to the plot
            TOOLTIP_TEXT_OFFSET = 20

            tooltip = ax.annotate(
                tooltip_text,
                xy=point,
                xytext=(0, 0),  # Initial position of the tooltip
                textcoords="offset pixels",
                bbox=dict(boxstyle="round", fc="w"),
                arrowprops=dict(arrowstyle="->"),
            )

            # Adjust tooltip position based on the region and the size of the text
            text_size = tooltip.get_window_extent()
            text_height = text_size.height
            text_width = text_size.width

            tooltip.xyann = (
                (-text_width / 2)
                + self.region[0] * (text_width / 2 + TOOLTIP_TEXT_OFFSET),
                (-text_height / 2)
                + self.region[1] * (text_height / 2 + TOOLTIP_TEXT_OFFSET),
            )

            self.tooltips.append(tooltip)

            event.canvas.draw_idle()
        return

    def clear_tooltips(self):
        """
        Clear all tooltips from the plot.
        This is useful to remove any existing tooltips before a new plot is drawn.
        """
        logger.debug("Clearing all tooltips")
        for tooltip in self.tooltips:
            tooltip.remove()
        self.tooltips.clear()
        self.canvas.draw_idle()
