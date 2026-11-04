from collections.abc import Iterable, Mapping
from typing import Any

from lcls_fel_model import load_model
from lume.model import LUMEModel
from lume.variables import Variable
from lume_pva.runner import PutMode, Runner
from lume_torch.base import LUMETorchModel


class FELSurrogate(LUMEModel):
    """LUME wrapper around the LCLS FEL surrogate model.

    Wraps the trained ``lcls_fel_model`` TorchModel, exposing all of its
    quadrupole, corrector, phase, and undulator input PVs as settable
    variables and the predicted FEL pulse energy ``GDET:FEE1:241:ENRC`` (mJ)
    as the output variable.
    """

    def __init__(self) -> None:
        super().__init__()
        self.surrogate = LUMETorchModel(load_model())

    def _get(self, names: Iterable[str]) -> dict[str, Any]:
        return self.surrogate.get(list(names))

    def _set(self, values: Mapping[str, Any]) -> None:
        self.surrogate.set(dict(values))

    @property
    def supported_variables(self) -> dict[str, Variable]:
        return self.surrogate.supported_variables

    def reset(self) -> None:
        self.surrogate.reset()


def main():
    model = FELSurrogate()
    # Ack puts only after the model has re-evaluated, so Badger's read of the
    # output right after caput(wait=True) sees the new value, not the stale one.
    # lume-pva defaults to PutMode.Immediate.
    config = Runner.generate_config(model, put_mode=PutMode.Complete)
    runner = Runner(model, config=config)
    runner.run()


if __name__ == "__main__":
    main()
