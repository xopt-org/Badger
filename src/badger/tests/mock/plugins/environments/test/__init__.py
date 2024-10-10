import torch
from badger import environment
from badger.errors import BadgerNoInterfaceError
import time


class Environment(environment.Environment):
    name = "test"
    variables = {f"x{i}": [-1, 1] for i in range(20)}
    observables = ["f", "c"]

    flag: int = 0
    delay: float = 0.0

    def set_variables(self, variable_inputs: dict[str, float]):
        if not self.interface:
            raise BadgerNoInterfaceError

        self.interface.set_values(variable_inputs)
        full_outputs = self.interface.get_values(self.variable_names)

        # Filling up the observations
        x = torch.tensor([full_outputs[f"x{i}"] for i in range(20)])
        self.interface.set_value("f", float((x**2).sum().numpy()))
        self.interface.set_value("c", float((x**2).sum().numpy()))
        time.sleep(self.delay)

    def get_bounds(self, variable_names):
        """
        Returns the bounds of new variables (not already included in env).
        """
        return {name: [-1, 1] for name in variable_names}
