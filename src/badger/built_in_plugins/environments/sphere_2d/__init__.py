from badger import environment
from PyQt5.QtNetwork import QNetworkRequest
from PyQt5.QtCore import QUrl


class Environment(environment.Environment):
    name = "sphere_2d"
    variables = {
        "x0": [-1, 1],
        "x1": [-1, 1],
    }
    observables = ["f"]

    _variables = {
        "x0": 0.5,
        "x1": 0.5,
    }
    _observations = {
        "f": 0.0,
    }

    def get_variables(self, variable_names):
        variable_outputs = {v: self._variables[v] for v in variable_names}

        return variable_outputs

    def set_variables(self, variable_inputs: dict[str, float]):
        for var, x in variable_inputs.items():
            self._variables[var] = x

        # Filling up the observations
        f = self._variables["x0"] ** 2 + self._variables["x1"] ** 2

        self._observations["f"] = f

    def get_observables(self, observable_names):
        return {k: self._observations[k] for k in observable_names}

    def search(self, keyword):
        url_string = (
            f"http://lcls-archapp.slac.stanford.edu/"
            f"retrieval/bpl/searchForPVsRegex?regex=.*{keyword}.*"
        )
        request = QNetworkRequest(QUrl(url_string))

        return request
