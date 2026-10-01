from badger import interface


class Interface(interface.Interface):
    name = "test"
    flag: int = 0

    # Private variables
    _states: dict[str, float]

    def __init__(self, **data: dict[str, float]) -> None:
        super().__init__(**data)

        self._states = {}

    @interface.log
    def get_values(self, channel_names: list[str]) -> dict[str, float]:
        channel_outputs = {}

        for channel in channel_names:
            try:
                value = self._states[channel]
            except KeyError:
                self._states[channel] = value = 0.5

            channel_outputs[channel] = value

        return channel_outputs

    @interface.log
    def set_values(self, channel_inputs: dict[str, float]) -> None:
        for channel, value in channel_inputs.items():
            self._states[channel] = value
