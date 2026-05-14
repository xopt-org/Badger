from pandas import DataFrame
from xopt.errors import FeasibilityError
from xopt.vocs import select_best

from badger.routine import Routine


def convert_to_solution(result: DataFrame, routine: Routine):
    vocs = routine.vocs
    try:
        best_idx, _, _ = select_best(vocs, routine.sorted_data, n=1)
        is_optimal = bool(best_idx.size > 0 and best_idx[0] == len(routine.data) - 1)
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
