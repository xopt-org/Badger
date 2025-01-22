from typing import Optional
from xopt import VOCS

from PyQt5.QtWidgets import (
    QTableWidgetItem,
)

from badger.routine import Routine

import logging

logger = logging.getLogger(__name__)


class ModelLogic:
    def __init__(self, routine: Optional[Routine], vocs: Optional[VOCS]):
        self.routine = routine
        self.vocs = vocs

    def update_routine(self, routine: Optional[Routine]):
        if routine is not None:
            self.routine = routine
            self.vocs = routine.vocs
        else:
            self.routine = None
            self.vocs = None
            logger.warning("Routine is None")

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
