from typing import Optional
from xopt import VOCS

from PyQt5.QtWidgets import (
    QTableWidgetItem,
)

from badger.routine import Routine


class ModelLogic:
    def __init__(self, xopt_obj: Routine, vocs: VOCS):
        self.xopt_obj = xopt_obj
        self.vocs = vocs

    def update_xopt(self, xopt_obj: Optional[Routine]):
        if xopt_obj is not None:
            self.xopt_obj = xopt_obj
            self.vocs = xopt_obj.vocs
        else:
            self.xopt_obj = None
            self.vocs = None
            print("Warning: xopt_obj is None in update_xopt")

    def get_reference_points(
        self, ref_inputs: list[QTableWidgetItem], variable_names: list[str]
    ):
        reference_point: dict[str, float] = {}
        if not self.vocs or not ref_inputs:
            return (
                reference_point  # Return empty if vocs or ref_inputs are not available
            )

        # Create a mapping from variable names to ref_inputs
        ref_inputs_dict = dict(zip(self.vocs.variable_names, ref_inputs))
        for var in self.vocs.variable_names:
            if var not in variable_names:
                ref_value = float(ref_inputs_dict[var].text())
                reference_point[var] = ref_value
        return reference_point
