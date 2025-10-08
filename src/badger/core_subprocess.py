from copy import deepcopy
import logging
import time
import traceback
from pandas import DataFrame
import multiprocessing as mp

from badger.settings import init_settings
from badger.errors import BadgerRunTerminated, BadgerEnvObsError
from badger.logger import _get_default_logger
from badger.logger.event import Events
from badger.routine import Routine

from xopt.errors import FeasibilityError, XoptError

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
        logger.debug(f"Selected best index: {best_idx}")
        if best_idx.size > 0:
            if best_idx[0] != len(routine.data) - 1:
                is_optimal = False
            else:
                is_optimal = True
        else:  # no feasible solution
            is_optimal = False
    except NotImplementedError:
        logger.warning(
            "select_best not implemented, disabling optimal highlight for MO problems"
        )
        is_optimal = False
    except FeasibilityError:  # no feasible data
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
    config_path: str = None,
    log_queue: mp.Queue = None,
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
    config_path: str
    log_queue: mp.Queue
    """

    # IMPORTANT: Configure subprocess logging FIRST, before any other logging calls
    if log_queue is not None:
        # Get log level from config
        temp_config = init_settings(config_path)
        log_level = temp_config.read_value("BADGER_LOGGING_LEVEL")
        
        # Configure subprocess logging with custom process name
        configure_subprocess_logger(
            log_queue=log_queue,
            logger_name="badger",
            log_level=log_level,
            process_name=f"OptWorker-{mp.current_process().pid}"
        )
    
    # Now all subsequent logger calls will go to the central queue
    logger.info(f"Subprocess started with PID {mp.current_process().pid}")
    
    # Initialize the settings singleton with the provided config path
    logger.info(f"Initializing settings with config path: {config_path}")
    init_settings(config_path)
    # Now load the archive would use the correct config
    from badger.archive import load_run, archive_run

    logger.info("Waiting for wait_event to be set...")
    wait_event.wait()

    try:
        args = queue.get(timeout=1)
        logger.debug(f"Received args from queue: {args}")
    except Exception as e:
        logger.error(f"Error in subprocess queue.get: {type(e).__name__}, {str(e)}")

    # set required arguments
    try:
        logger.info(f"Loading routine from file: {args['routine_filename']}")
        routine = load_run(args["routine_filename"])
        logger.info("Resetting environment global state")
        routine.environment.reset_environment()
        if routine.vrange_hard_limit:
            logger.info(
                f"Updating environment variables with hard limits: {routine.vrange_hard_limit}"
            )
            routine.environment.variables.update(routine.vrange_hard_limit)
        if routine.data is not None:
            logger.info("Resetting routine data")
            routine.data = routine.data.iloc[0:0]
    except Exception as e:
        error_title = f"{type(e).__name__}: {e}"
        error_traceback = traceback.format_exc()
        logger.error(f"Error initializing routine: {error_title}\n{error_traceback}")
        queue.put((error_title, error_traceback))
        raise e

    # TODO look into this bug with serializing of turbo. Fix might be needed in Xopt
    # Patch for converting dtype str to torch object
    try:
        dtype = routine.generator.turbo_controller.tkwargs["dtype"]
        logger.debug(f"Converting turbo_controller dtype from str to object: {dtype}")
        routine.generator.turbo_controller.tkwargs["dtype"] = eval(dtype)
    except AttributeError:
        logger.warning("AttributeError when converting turbo_controller dtype")
        pass
    except KeyError:
        logger.warning("KeyError when converting turbo_controller dtype")
        pass
    except TypeError:
        logger.warning("TypeError when converting turbo_controller dtype")
        pass

    # Assign the initial points and bounds
    logger.info(f"Setting routine variable ranges: {args['variable_ranges']}")
    routine.vocs.variables = args["variable_ranges"]
    logger.info("Setting routine initial points")
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
    logger.info(f"Getting default logger with verbosity: {verbose}")
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
    logger.info("Optimization started")
    opt_logger.update(Events.OPTIMIZATION_START, solution_meta)

    # evaluate initial points:
    # timeout logic will be handled in the specific environment
    try:
        logger.info("Evaluating initial points...")
        for _, ele in initial_points.iterrows():
            logger.debug(f"Evaluating initial point: {ele.to_dict()}")
            result = routine.evaluate_data(ele.to_dict())
            solution = convert_to_solution(result, routine)
            opt_logger.update(Events.OPTIMIZATION_STEP, solution)
            if evaluate:
                time.sleep(0.1)
                evaluate_queue[0].send((routine.data, routine.generator))

        logger.info("Starting optimization loop...")
        while True:
            if stop_process.is_set():
                logger.info("Stop process set. Terminating optimization.")
                evaluate_queue[0].close()
                raise BadgerRunTerminated
            elif not pause_process.is_set():
                logger.info("Pause process not set. Waiting...")
                pause_process.wait()

            if termination_condition and start_time:
                tc_config = termination_condition
                idx = tc_config["tc_idx"]
                if idx == 0:
                    max_eval = tc_config["max_eval"]
                    logger.debug(
                        f"Checking max_eval termination: {len(routine.data)} >= {max_eval}"
                    )
                    if len(routine.data) >= max_eval:
                        logger.info(
                            "Max evaluations reached. Terminating optimization."
                        )
                        raise BadgerRunTerminated
                elif idx == 1:
                    max_time = tc_config["max_time"]
                    dt = time.time() - start_time
                    logger.debug(f"Checking max_time termination: {dt} >= {max_time}")
                    if dt >= max_time:
                        logger.info("Max time reached. Terminating optimization.")
                        raise BadgerRunTerminated

            candidates = routine.generator.generate(1)[0]
            logger.debug(f"Generated candidates: {candidates}")
            candidates = DataFrame(candidates, index=[0])

            if stop_process.is_set():
                logger.info("Stop process set during optimization loop. Terminating.")
                evaluate_queue[0].close()
                raise BadgerRunTerminated
            elif not pause_process.is_set():
                logger.info(
                    "Pause process not set during optimization loop. Waiting..."
                )
                pause_process.wait()

            result = routine.evaluate_data(candidates)
            solution = convert_to_solution(result, routine)
            opt_logger.update(Events.OPTIMIZATION_STEP, solution)

            generator_copy = deepcopy(routine.generator)

            if evaluate:
                logger.debug("Sending evaluation data to evaluate_queue.")
                evaluate_queue[0].send((routine.data, generator_copy))

            if archive:
                if not testing:
                    logger.info("Archiving run state.")
                    archive_run(routine)

    except BadgerRunTerminated:
        logger.info("Optimization terminated by BadgerRunTerminated.")
        opt_logger.update(Events.OPTIMIZATION_END, solution_meta)
        evaluate_queue[0].close()
    except XoptError as e:
        logger.error(f"XoptError during optimization: {e}")
        opt_logger.update(Events.OPTIMIZATION_END, solution_meta)
        error_title = "BadgerEnvObsError: There was an error getting observables from the environment. See the traceback for more details."
        queue.put((error_title, traceback.format_exc()))
        evaluate_queue[0].close()
        raise BadgerEnvObsError(e)
    except Exception as e:
        logger.error(
            f"Unhandled exception during optimization: {type(e).__name__}: {e}\n{traceback.format_exc()}"
        )
        opt_logger.update(Events.OPTIMIZATION_END, solution_meta)
        error_title = f"{type(e).__name__}: {e}"
        error_traceback = traceback.format_exc()
        queue.put((error_title, error_traceback))
        evaluate_queue[0].close()
        raise e
