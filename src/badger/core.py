import time
from typing import Callable

from pandas import concat, DataFrame

from badger.errors import BadgerRunTerminated
from badger.logger import _get_default_logger
from badger.logger.event import Events
from badger.routine import Routine
from badger.utils import curr_ts_to_str, dump_state


def check_run_status(active_callback):
    while True:
        status = active_callback()
        if status == 2:
            raise BadgerRunTerminated
        elif status == 1:
            time.sleep(0)
            continue
        else:
            break


def convert_to_solution(result: DataFrame, routine: Routine):
    vocs = routine.vocs
    try:
        best_idx, _, _ = vocs.select_best(routine.sorted_data, n=1)
        if best_idx.size > 0:
            best_idx = int(best_idx[0])  # convert numpy array to int
            if best_idx != len(routine.data) - 1:
                is_optimal = False
            else:
                is_optimal = True
        else:  # no feasible solution
            is_optimal = False
    except NotImplementedError:
        is_optimal = False  # disable the optimal highlight for MO problems
    except IndexError:  # no feasible solution
        is_optimal = False

    vars = list(result[vocs.variable_names].to_numpy()[0])
    objs = list(result[vocs.objective_names].to_numpy()[0])
    cons = list(result[vocs.constraint_names].to_numpy()[0])
    stas = list(result[vocs.observable_names].to_numpy()[0])

    solution = (
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

    return solution


def run_routine(
    routine: Routine,
    active_callback: Callable,
    generate_callback: Callable,
    evaluate_callback: Callable,
    states_callback: Callable,
    dump_file_callback: Callable = None,
    verbose: int = 2,
) -> None:
    """
    Run the provided routine object using Xopt.

    Parameters
    ----------
    routine : Routine
        Routine object created by Badger GUI to run optimization.

    active_callback : Callable
        Callback function that returns an int denoting if
        optimization/evaluation should proceed.
        0: proceed
        1: paused
        2: killed

    generate_callback : Callable
        Callback function called after generating candidate points that takes
        the form `f(generator: Generator, candidates: DataFrame)`.

    evaluate_callback : Callable
        Callback function called after evaluating points that takes the form
        `f(data: DataFrame)`.

    states_callback : Callable
        Callback function called after system states is fetched
    """

    environment = routine.environment
    initial_points = routine.initial_points

    # Log the optimization progress in terminal
    opt_logger = _get_default_logger(verbose)

    # Save system states if applicable
    states = environment.get_system_states()
    if states_callback and (states is not None):
        states_callback(states)

    # Optimization starts
    solution_meta = (
        None,
        None,
        None,
        None,
        None,
        routine.vocs.variable_names,
        routine.vocs.objective_names,
        routine.vocs.constraint_names,
        routine.vocs.observable_names,
    )
    opt_logger.update(Events.OPTIMIZATION_START, solution_meta)

    # evaluate initial points:
    # Nikita: more care about the setting var logic,
    # wait or consider timeout/retry
    for _, ele in initial_points.iterrows():
        result = routine.evaluate_data(ele.to_dict())
        solution = convert_to_solution(result, routine)
        opt_logger.update(Events.OPTIMIZATION_STEP, solution)
        if evaluate_callback:
            evaluate_callback(result)

    # Prepare for dumping file
    if dump_file_callback:
        combined_results = None
        ts_start = curr_ts_to_str()
        dump_file = dump_file_callback()
        if not dump_file:
            dump_file = f"xopt_states_{ts_start}.yaml"

    # perform optimization
    try:
        while True:
            status = active_callback()
            if status == 2:
                raise BadgerRunTerminated
            elif status == 1:
                time.sleep(0)
                continue

            # generate points to observe
            candidates = routine.generator.generate(1)[0]
            candidates = DataFrame(candidates, index=[0])
            # generate_callback(generator, candidates)
            generate_callback(candidates)

            check_run_status(active_callback)
            # if still active evaluate the points and add to generator
            # check active_callback evaluate point
            result = routine.evaluate_data(candidates)
            solution = convert_to_solution(result, routine)
            opt_logger.update(Events.OPTIMIZATION_STEP, solution)
            if evaluate_callback:
                evaluate_callback(result)

            # Dump Xopt state after each step
            if dump_file_callback:
                if combined_results is not None:
                    combined_results = concat(
                        [combined_results, result], axis=0
                    ).reset_index(drop=True)
                else:
                    combined_results = result

                dump_state(dump_file, routine.generator, combined_results)
    except Exception as e:
        opt_logger.update(Events.OPTIMIZATION_END, solution_meta)
        raise e
