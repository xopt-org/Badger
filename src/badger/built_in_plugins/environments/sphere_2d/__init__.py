from badger import environment


class Environment(environment.Environment):
    name = "sphere_2d"
    variables = {
        "x0": [-1, 1],
        "x1": [-1, 1],
    }
    observables = ["f1", "f2"]

    _variables = {
        "x0": 0.5,
        "x1": 0.5,
    }
    _observations = {
        "f1": 0.0,
        "f2": 0.0,
    }

    def get_variables(self, variable_names):
        variable_outputs = {v: self._variables[v] for v in variable_names}

        return variable_outputs

    def set_variables(self, variable_inputs: dict[str, float]):
        for var, x in variable_inputs.items():
            self._variables[var] = x

        # Filling up the observations
        f1 = self._variables["x0"] ** 2 + self._variables["x1"] ** 2
        f2 = (self._variables["x0"] - 0.5) ** 2 + self._variables["x1"] ** 2

        self._observations["f1"] = f1
        self._observations["f2"] = f2

    def get_observables(self, observable_names):
        return {k: self._observations[k] for k in observable_names}
