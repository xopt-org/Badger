from badger import interface
from typing import Dict


class Interface(interface.Interface):
    name = "test"
    flag: int = 0

    # Private variables
    _states: Dict

    def __init__(self, **data):
        super().__init__(**data)

        self._states = {}

    @interface.log
    def get_values(self, channel_names):
        channel_outputs = {}

        for channel in channel_names:
            try:
                value = self._states[channel]
            except KeyError:
                self._states[channel] = value = 0.5

            channel_outputs[channel] = value

        return channel_outputs

    @interface.log
    def set_values(self, channel_inputs):
        for channel, value in channel_inputs.items():
            self._states[channel] = value
