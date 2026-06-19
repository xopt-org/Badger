"""LCLS FEL pulse-energy surrogate environment.

Wraps the LUME-torch surrogate model from the `lcls_fel_model` package. All
341 model inputs are exposed as Badger variables (bounds taken from the model's
value ranges, starting values from its defaults), and the single model output
(GDET:FEE1:241:ENRC, FEL pulse energy in mJ) is exposed as an observable.
"""

from badger import environment
from lcls_fel_model import load_model

_model = load_model()


class Environment(environment.Environment):
    name = "lcls_fel_surrogate"

    variables = {
        var.name: [float(var.value_range[0]), float(var.value_range[1])]
        for var in _model.input_variables
    }
    observables = list(_model.output_names)

    _variables = {var.name: float(var.default_value) for var in _model.input_variables}

    def get_variables(self, variable_names):
        return {name: self._variables[name] for name in variable_names}

    def set_variables(self, variable_inputs: dict[str, float]):
        self._variables.update(variable_inputs)

    def get_observables(self, observable_names):
        prediction = _model.evaluate(self._variables)
        return {name: float(prediction[name]) for name in observable_names}
