from copy import deepcopy
import logging
import time
import traceback
import torch  # noqa: F401. For converting dtype str to torch object.
from pandas import DataFrame
import multiprocessing as mp

from badger.archive import load_run
from badger.errors import BadgerRunTerminated
from badger.logger import _get_default_logger
from badger.logger.event import Events
from badger.routine import Routine
from badger.archive import archive_run

logger = logging.getLogger(__name__)


def convert_to_solution(result: DataFrame, routine: Routine):
    """
    This method is passed the latest evaluated solution and converts that to a printable format for the terminal.
    This method is for the GUI version of Badger.

    Parameters
    ----------
    result : DataFrame
    routine : Routine
    """
    vocs = routine.vocs
    try:
        best_idx, _, _ = vocs.select_best(routine.sorted_data, n=1)

        if best_idx.size > 0:
            if best_idx[0] != len(routine.data) - 1:
                is_optimal = False
            else:
                is_optimal = True
        else:  # no feasible solution
            is_optimal = False
    except NotImplementedError:
        is_optimal = False  # disable the optimal highlight for MO problems
    except IndexError:  # no feasible data
        logger.info("no feasible solutions found")
        is_optimal = False

    vars = list(result[vocs.variable_names].to_numpy()[0])
    objs = list(result[vocs.objective_names].to_numpy()[0])
    cons = list(result[vocs.constraint_names].to_numpy()[0])
    stas = list(result[vocs.observable_names].to_numpy()[0])

    # TODO: This structure needs improvement
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


def run_routine_subprocess(
    queue: mp.Queue,
    evaluate_queue: mp.Pipe,
    stop_process: mp.Event,
    pause_process: mp.Event,
    wait_event: mp.Event,
) -> None:
    """
    Run the provided routine object using Xopt. This method is run as a subproccess

    Parameters
    ----------
    queue: mp.Queue
    evaluate_queue: mp.Pipe
    stop_process: mp.Event
    pause_process: mp.Event
    wait_event: mp.Event
    """
    wait_event.wait()

    try:
        args = queue.get(timeout=1)
    except Exception as e:
        print(f"Error in subprocess: {type(e).__name__}, {str(e)}")

    # set required arguments
    try:
        routine = load_run(args["routine_filename"])
        # TODO: might need to consider the case where routine.data is None?
        if routine.data is not None:
            routine.data = routine.data.iloc[0:0]  # reset the data
    except Exception as e:
        error_title = f"{type(e).__name__}: {e}"
        error_traceback = traceback.format_exc()
        queue.put((error_title, error_traceback))
        raise e

    # TODO look into this bug with serializing of turbo. Fix might be needed in Xopt
    # Patch for converting dtype str to torch object
    try:
        dtype = routine.generator.turbo_controller.tkwargs["dtype"]
        routine.generator.turbo_controller.tkwargs["dtype"] = eval(dtype)
    except AttributeError:
        pass
    except KeyError:
        pass
    except TypeError:
        pass

    # Assign the initial points and bounds
    routine.vocs.variables = args["variable_ranges"]
    routine.initial_points = args["initial_points"]

    # set optional arguments
    evaluate = args.pop("evaluate", None)
    archive = args.pop("archive", False)
    termination_condition = args.pop("termination_condition", None)
    start_time = args.pop("start_time", None)
    verbose = args.pop("verbose", 2)
    testing = args.pop("testing", False)

    # setup variables of routine properties for code readablilty
    initial_points = routine.initial_points

    # Log the optimization progress in terminal
    opt_logger = _get_default_logger(verbose)

    # Optimization starts
    # This is used by the logger to print to the terminal.
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
    # timeout logic will be handled in the specific environment
    for _, ele in initial_points.iterrows():
        result = routine.evaluate_data(ele.to_dict())
        solution = convert_to_solution(result, routine)
        opt_logger.update(Events.OPTIMIZATION_STEP, solution)
        if evaluate:
            time.sleep(0.1)  # give it some break tp catch up
            evaluate_queue[0].send((routine.data, routine.generator))

    # perform optimization
    try:
        while True:
            if stop_process.is_set():
                evaluate_queue[0].close()
                raise BadgerRunTerminated
            elif not pause_process.is_set():
                pause_process.wait()

            # Check if termination condition has been satisfied
            if termination_condition and start_time:
                tc_config = termination_condition
                idx = tc_config["tc_idx"]
                if idx == 0:
                    max_eval = tc_config["max_eval"]
                    if len(routine.data) >= max_eval:
                        raise BadgerRunTerminated
                elif idx == 1:
                    max_time = tc_config["max_time"]
                    dt = time.time() - start_time
                    if dt >= max_time:
                        raise BadgerRunTerminated

            # TODO give user a message that a solution is being worked on.

            # generate points to observe
            candidates = routine.generator.generate(1)[0]
            candidates = DataFrame(candidates, index=[0])

            # TODO timer off + new timer for evaluate
            # TODO solution being evaluated

            # External triggers
            if stop_process.is_set():
                evaluate_queue[0].close()
                raise BadgerRunTerminated
            elif not pause_process.is_set():
                pause_process.wait()

            # if still active evaluate the points and add to generator
            # check active_callback evaluate point
            result = routine.evaluate_data(candidates)
            solution = convert_to_solution(result, routine)
            opt_logger.update(Events.OPTIMIZATION_STEP, solution)

            generator_copy = deepcopy(routine.generator)

            if evaluate:
                evaluate_queue[0].send((routine.data, generator_copy))

            # archive Xopt state after each step
            if archive:
                if not testing:
                    archive_run(routine)
    except BadgerRunTerminated:
        opt_logger.update(Events.OPTIMIZATION_END, solution_meta)
        evaluate_queue[0].close()
    except Exception as e:
        opt_logger.update(Events.OPTIMIZATION_END, solution_meta)
        error_title = f"{type(e).__name__}: {e}"
        error_traceback = traceback.format_exc()
        queue.put((error_title, error_traceback))
        evaluate_queue[0].close()
        raise e
