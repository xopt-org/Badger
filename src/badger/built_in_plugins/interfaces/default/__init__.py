"""In-memory interface that stores channel values in a plain dict.
Used by test environments and as the fallback when no hardware
interface is configured."""

from typing import Any

from badger import interface


class Interface(interface.Interface):
    name = "default"
    # If params not specified, it would be an empty dict

    # Private variables
    _states: dict[str, float | list[float]]

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)

        self._states: dict[str, float | list[float]] = {}

    def get_values(self, channel_names: list[str]) -> dict[str, float | list[float]]:
        channel_outputs = {}

        for channel in channel_names:
            try:
                value = self._states[channel]
            except KeyError:
                self._states[channel] = value = 0

            channel_outputs[channel] = value

        return channel_outputs

    def set_values(self, channel_inputs: dict[str, float | list[float]]) -> None:
        for channel, value in channel_inputs.items():
            self._states[channel] = value
