import logging
logger = logging.getLogger(__name__)
import os
import sys
import time
import signal
import pandas as pd
from coolname import generate_slug
from ..utils import load_config, merge_params
from ..utils import config_list_to_dict, curr_ts, ts_to_str
from ..core import run_routine as run
#from ..core import normalize_routine
from ..settings import read_value


def run_n_archive(routine, yes=False, save=False, verbose=2,
                  fmt='lcls-log-full', sleep=0, flush_prompt=False):
    try:
        from ..archive import archive_run
    except Exception as e:
        logger.error(e)
        return

    var_names = [next(iter(d)) for d in routine['config']['variables']]
    obj_names = [next(iter(d)) for d in routine['config']['objectives']]
    if routine['config']['constraints']:
        con_names = [next(iter(d)) for d in routine['config']['constraints']]
    else:
        con_names = []
    try:
        sta_names = routine['config']['states'] or []
    except KeyError:  # this would happen when rerun an old version routine
        sta_names = []
    # Store solutions in a list to avoid global var def
    solutions = []
    # Store system states and other stuff
    storage = {
        'states': None,
        'env': None,
        'ts_last_dump': None,
        'paused': False,
    }

    def handler(*args):
        if storage['paused']:
            print('')  # start a new line
            if flush_prompt:  # erase the last prompt
                sys.stdout.write('\033[F')
            raise Exception('Optimization run has been terminated!')
        storage['paused'] = True

    signal.signal(signal.SIGINT, handler)

    def before_evaluate(vars):
        if storage['paused']:
            res = input('Optimization paused. Press Enter to resume or Ctrl/Cmd + C to terminate: ')
            while res != '':
                if flush_prompt:
                    sys.stdout.write('\033[F')
                res = input(f'Invalid choice: {res}. Please press Enter to resume or Ctrl/Cmd + C to terminate: ')
            if flush_prompt:
                sys.stdout.write('\033[F')
        storage['paused'] = False

    def after_evaluate(vars, obses, cons, stas):
        # vars: ndarray
        # obses: ndarray
        # cons: ndarray
        # stas: list
        ts = curr_ts()
        ts_float = ts.timestamp()
        solution = [ts_float, ts_to_str(ts, fmt)] + list(obses) + list(cons) + list(vars) + stas
        solutions.append(solution)

        # Try dump the run data and interface log to the disk
        dump_period = read_value('BADGER_DATA_DUMP_PERIOD')
        ts_last_dump = storage['ts_last_dump']
        if (ts_last_dump is None) or (ts_float - ts_last_dump > dump_period):
            storage['ts_last_dump'] = ts_float
            df = pd.DataFrame(solutions, columns=['timestamp_raw', 'timestamp'] + obj_names + con_names + var_names + sta_names)
            _run = archive_run(routine, df, storage['states'])
            # Try dump the interface logs
            try:
                path = _run['path']
                filename = _run['filename'][:-4] + 'pickle'
                storage['env'].interface.dump_recording(os.path.join(path, filename))
            except:
                pass

        # take a break to let the outside signal to change the status
        time.sleep(sleep)

    def states_ready(states):
        storage['states'] = states

    def env_ready(env):
        storage['env'] = env

    try:
        run(routine, yes, save, verbose,
            before_evaluate=before_evaluate, after_evaluate=after_evaluate,
            states_ready=states_ready, env_ready=env_ready)
    except Exception as e:
        if str(e) == 'Optimization run has been terminated!':
            logger.info(e)
        else:
            logger.error(e)

    if solutions:  # only save the run when at least one solution has been evaluated
        df = pd.DataFrame(solutions, columns=['timestamp_raw', 'timestamp'] + obj_names + con_names + var_names + sta_names)
        _run = archive_run(routine, df, storage['states'])
        # Try dump the interface logs
        try:
            path = _run['path']
            filename = _run['filename'][:-4] + 'pickle'
            storage['env'].interface.stop_recording(os.path.join(path, filename))
        except:
            pass


def run_routine(args):
    try:
        from ..factory import get_algo, get_env
    except Exception as e:
        logger.error(e)
        return

    try:
        # Get env params
        _, configs_env = get_env(args.env)

        # Get algo params
        _, configs_algo = get_algo(args.algo)

        # Normalize the algo and env params
        params_env = load_config(args.env_params)
        params_algo = load_config(args.algo_params)
    except Exception as e:
        logger.error(e)
        return
    params_env = merge_params(configs_env['params'], params_env)
    params_algo = merge_params(configs_algo['params'], params_algo)

    # Load routine configs
    try:
        configs_routine = load_config(args.config)
    except Exception as e:
        logger.error(e)
        return

    # Compose the routine
    routine = {
        'name': args.save or generate_slug(2),
        'algo': args.algo,
        'env': args.env,
        'algo_params': params_algo,
        'env_params': params_env,
        # env_vranges is an additional info for the normalization
        # Will be removed after the normalization
        'env_vranges': config_list_to_dict(configs_env['variables']),
        'config': configs_routine,
    }

    # Sanity check and config normalization
    try:
        routine = normalize_routine(routine)
    except Exception as e:
        logger.error(e)
        return

    run_n_archive(routine, args.yes, args.save, args.verbose)
