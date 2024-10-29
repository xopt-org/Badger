import torch
from badger import environment
from badger.errors import BadgerNoInterfaceError


class Environment(environment.Environment):
    name = "multiobjective_test"
    variables = {f"x{i}": [-1, 1] for i in range(20)}
    observables = ["f1", "f2"]

    flag: int = 0

    def set_variables(self, variable_inputs: dict[str, float]):
        if not self.interface:
            raise BadgerNoInterfaceError

        self.interface.set_values(variable_inputs)
        full_outputs = self.interface.get_values(self.variable_names)

        # Filling up the observations
        x = torch.tensor([full_outputs[f"x{i}"] for i in range(20)])
        self.interface.set_values(
            {
                "f1": float((x**2).sum().numpy()),
                "f2": float((x**3).sum().numpy()),
            }
        )
