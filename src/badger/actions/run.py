import logging
import os
import sys
import time
import signal

from pandas import DataFrame

from badger.utils import curr_ts
from badger.core import run_routine as run
from badger.routine import Routine
from badger.settings import init_settings
from badger.errors import BadgerRunTerminated

logger = logging.getLogger(__name__)


def run_n_archive(
    routine: Routine, yes=False, save=False, verbose=2, sleep=0, flush_prompt=False
):
    try:
        from badger.archive import archive_run
    except Exception as e:
        logger.error(e)
        return

    # Store system states and other stuff
    storage = {
        "states": None,
        "ts_last_dump": None,
        "paused": False,
    }

    def handler(*args):
        if storage["paused"]:
            print("")  # start a new line
            if flush_prompt:  # erase the last prompt
                sys.stdout.write("\033[F")
            raise BadgerRunTerminated
        storage["paused"] = True

    signal.signal(signal.SIGINT, handler)

    def check_run_status():
        return 0

    def before_evaluate(candidates: DataFrame):
        if storage["paused"]:
            res = input(
                "Optimization paused. Press Enter to resume or Ctrl/Cmd + C to terminate: "
            )
            while res != "":
                if flush_prompt:
                    sys.stdout.write("\033[F")
                res = input(
                    f"Invalid choice: {res}. Please press Enter to resume or Ctrl/Cmd + C to terminate: "
                )
            if flush_prompt:
                sys.stdout.write("\033[F")
        storage["paused"] = False

    def after_evaluate(data: DataFrame):
        # vars: ndarray
        # obses: ndarray
        # cons: ndarray
        # stas: list
        ts = curr_ts()
        ts_float = ts.timestamp()
        config = init_settings()
        # Try dump the run data and interface log to the disk
        dump_period = float(config.read_value("BADGER_DATA_DUMP_PERIOD"))
        ts_last_dump = storage["ts_last_dump"]
        if (ts_last_dump is None) or (ts_float - ts_last_dump > dump_period):
            storage["ts_last_dump"] = ts_float
            _run = archive_run(routine, storage["states"])
            # Try dump the interface logs
            try:
                path = _run["path"]
                filename = _run["filename"][:-4] + "pickle"
                routine.environment.interface.dump_recording(
                    os.path.join(path, filename)
                )
            except Exception:
                pass

        # take a break to let the outside signal to change the status
        time.sleep(sleep)

    def states_ready(states):
        storage["states"] = states

    try:
        run(
            routine,
            active_callback=check_run_status,
            generate_callback=before_evaluate,
            evaluate_callback=after_evaluate,
            states_callback=states_ready,
        )
    except BadgerRunTerminated as e:
        logger.info(e)
    except Exception as e:
        logger.error(e)

    # Save the run when at least one solution has been evaluated
    if len(routine.data):
        _run = archive_run(routine, storage["states"])
        # Try dump the interface logs
        try:
            path = _run["path"]
            filename = _run["filename"][:-4] + "pickle"
            routine.environment.interface.stop_recording(os.path.join(path, filename))
        except Exception:
            pass


def run_routine(args):
    pass
    # try:
    #     from ..factory import get_algo, get_env
    # except Exception as e:
    #     logger.error(e)
    #     return

    # try:
    #     # Get env params
    #     _, configs_env = get_env(args.env)

    #     # Get algo params
    #     _, configs_algo = get_algo(args.algo)

    #     # Normalize the algo and env params
    #     params_env = load_config(args.env_params)
    #     params_algo = load_config(args.algo_params)
    # except Exception as e:
    #     logger.error(e)
    #     return
    # params_env = merge_params(configs_env['params'], params_env)
    # params_algo = merge_params(configs_algo['params'], params_algo)

    # # Load routine configs
    # try:
    #     configs_routine = load_config(args.config)
    # except Exception as e:
    #     logger.error(e)
    #     return

    # # Compose the routine
    # routine = {
    #     'name': args.save or generate_slug(2),
    #     'algo': args.algo,
    #     'env': args.env,
    #     'algo_params': params_algo,
    #     'env_params': params_env,
    #     # env_vranges is an additional info for the normalization
    #     # Will be removed after the normalization
    #     'env_vranges': config_list_to_dict(configs_env['variables']),
    #     'config': configs_routine,
    # }

    # run_n_archive(routine, args.yes, args.save, args.verbose)
