from typing import TYPE_CHECKING

from pandas import DataFrame
from xopt.errors import FeasibilityError
from xopt.vocs import select_best

if TYPE_CHECKING:
    from badger.routine import Routine


def convert_to_solution(result: DataFrame, routine: "Routine"):
    """
    Convert a single-row evaluation result into the tuple format expected by
    Badger's terminal/logger output.

    Parameters
    ----------
    result : DataFrame
        A single evaluated candidate row.
    routine : Routine
        Routine object containing current VOCS and accumulated data.

    Returns
    -------
    tuple
        (variables, objectives, constraints, observables, is_optimal,
        variable_names, objective_names, constraint_names, observable_names)
    """
    vocs = routine.vocs
    try:
        best_idx, _, _ = select_best(vocs, routine.sorted_data, n=1)
        # Highlight this point only when the latest row is also the current best.
        # `select_best` indexes into `routine.sorted_data`; this check ensures the
        # best point corresponds to the latest row in underlying routine data.
        is_latest_best = best_idx.size > 0 and best_idx[0] == len(routine.data) - 1
        is_optimal = bool(is_latest_best)
    except (NotImplementedError, FeasibilityError, IndexError):
        is_optimal = False

    vars = list(result[vocs.variable_names].to_numpy()[0])
    objs = list(result[vocs.objective_names].to_numpy()[0])
    cons = list(result[vocs.constraint_names].to_numpy()[0])
    stas = list(result[vocs.observable_names].to_numpy()[0])

    return (
        vars,
        objs,
        cons,
        stas,
        is_optimal,
        vocs.variable_names,
        vocs.objective_names,
        vocs.constraint_names,
        vocs.observable_names,
    )
