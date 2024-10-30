from badger import interface


class Interface(interface.Interface):
    name = "default"
    # If params not specified, it would be an empty dict

    # Private variables
    _states: dict

    def __init__(self, **data):
        super().__init__(**data)

        self._states = {}

    def get_values(self, channel_names):
        channel_outputs = {}

        for channel in channel_names:
            try:
                value = self._states[channel]
            except KeyError:
                self._states[channel] = value = 0

            channel_outputs[channel] = value

        return channel_outputs

    def set_values(self, channel_inputs):
        for channel, value in channel_inputs.items():
            self._states[channel] = value
