import pickle
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, List

from pydantic import BaseModel

from badger.utils import curr_ts


def log(func):
    def func_log(*args, **kwargs):
        if func.__name__ == "set_values":
            if "channel_inputs" in kwargs.keys():
                channel_inputs = kwargs["channel_inputs"]
            else:
                channel_inputs = args[1]
            args[0]._logs.append(
                {
                    "timestamp": curr_ts().timestamp(),
                    "action": "set_values",
                    "channel_inputs": channel_inputs,
                }
            )

            return func(*args, **kwargs)
        elif func.__name__ == "get_values":
            channel_outputs = func(*args, **kwargs)
            args[0]._logs.append(
                {
                    "timestamp": curr_ts().timestamp(),
                    "action": "get_values",
                    "channel_outputs": channel_outputs,
                }
            )

            return channel_outputs
        else:
            return func(*args, **kwargs)

    return func_log


class Interface(BaseModel, ABC):
    name: ClassVar[str]
    # Put interface params here
    # params: float = Field(..., description='Example intf parameter')

    # Private variables
    _logs: List[Dict] = []  # TODO: Add a property for it?

    def start_recording(self):
        self._logs = []

    def stop_recording(self, filename):
        # Do not create the pickle file if log is empty
        # This usually happens when the log decorator is not used in the
        # specific interface
        if not self._logs:
            return

        with open(filename, "wb") as f:
            pickle.dump(self._logs, f)

        self._logs = []

    def dump_recording(self, filename):
        # Dump the logs to disk w/o cleaning up the log history
        if not self._logs:
            return

        with open(filename, "wb") as f:
            pickle.dump(self._logs, f)

    # Environment should only call this method to get channels
    @abstractmethod
    def get_values(self, channel_names: List[str]) -> Dict[str, Any]:
        pass

    # Environment should only call this method to set channels
    @abstractmethod
    def set_values(self, channel_inputs: Dict[str, Any]):
        pass

    def get_value(self, channel_name: str, **kwargs) -> Any:
        return self.get_values([channel_name], **kwargs)[channel_name]

    def set_value(self, channel_name: str, channel_value, **kwargs):
        return self.set_values({channel_name: channel_value}, **kwargs)
