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
    print(
        "This command is deprecated.\n"
        "Please use 'badger -g' to launch the Badger GUI "
        "and run an optimization."
    )
    return

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


def run_routine_gui(routine, auto_run=False):
    """
    Launch ACR GUI with pre-loaded routine.

    Args:
        routine: Routine object to load
        auto_run: If True, automatically start optimization after loading
    """
    from badger.gui.acr import launch_gui
    launch_gui(routine=routine, auto_run=auto_run)


def run_routine_headless(routine, auto_run=False, verbose=2):
    """
    Run routine in headless mode using subprocess.

    Args:
        routine: Routine object to run
        auto_run: If True, skip confirmation prompt
        verbose: Verbosity level (0, 1, or 2)
    """
    from multiprocessing import Process, Queue, Event
    from badger.core_subprocess import run_routine_subprocess
    from badger.archive import archive_run
    import tempfile
    from badger.utils import get_yaml_string

    # Display routine summary
    print(f"\n{'='*60}")
    print(f"Routine: {routine.name}")
    print(f"Environment: {routine.environment.name}")
    print(f"Generator: {routine.generator.name}")
    print(f"Variables: {list(routine.vocs.variables.keys())}")
    print(f"Objectives: {list(routine.vocs.objectives.keys())}")
    if routine.vocs.constraints:
        print(f"Constraints: {list(routine.vocs.constraints.keys())}")
    print(f"{'='*60}\n")

    # Ask for confirmation if not auto_run
    if not auto_run:
        try:
            response = input("Start optimization? [y/N]: ")
            if response.lower() != 'y':
                print("Cancelled.")
                return
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return

    # Set up subprocess communication
    data_queue = Queue()
    stop_event = Event()
    pause_event = Event()
    pause_event.set()  # Start unpaused

    # Save routine temporarily to file
    routine_filename = tempfile.mktemp(suffix='.yaml')
    with open(routine_filename, 'w') as f:
        # Convert routine to YAML
        routine_dict = routine.model_dump(mode='json')
        f.write(get_yaml_string(routine_dict))

    # Start subprocess
    start_time = time.time()
    process = Process(
        target=run_routine_subprocess,
        args=(
            data_queue,
            stop_event,
            pause_event,
            routine_filename,
            True,  # archive
            None,  # termination_condition (could add from args)
            start_time,
            False,  # testing
        )
    )
    process.start()

    # Monitor progress
    print("Optimization started. Press Ctrl+C to stop.\n")
    iteration = 0
    last_data = None

    try:
        while process.is_alive():
            time.sleep(0.1)

            # Check for data from subprocess
            while not data_queue.empty():
                data_dict = data_queue.get()

                if 'error' in data_dict:
                    print(f"\n❌ Error: {data_dict['error']}")
                    break

                if 'data' in data_dict:
                    # Display progress
                    df = data_dict['data']
                    if last_data is None or len(df) > len(last_data):
                        iteration = len(df)
                        last_row = df.iloc[-1]

                        print(f"Iteration {iteration}:")
                        for var_name in routine.vocs.variables:
                            if var_name in last_row:
                                print(f"  {var_name}: {last_row[var_name]:.4f}")
                        for obj_name in routine.vocs.objectives:
                            if obj_name in last_row:
                                print(f"  {obj_name}: {last_row[obj_name]:.4f}")
                        print()

                        last_data = df

    except KeyboardInterrupt:
        print("\n\nStopping optimization...")
        stop_event.set()

    # Wait for completion
    process.join(timeout=5)
    if process.is_alive():
        process.terminate()
        process.join()

    # Final status
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"Optimization completed in {elapsed:.2f}s")
    print(f"Total iterations: {iteration}")
    print(f"{'='*60}\n")

    # Clean up
    if os.path.exists(routine_filename):
        os.remove(routine_filename)


def run_routine_cli(args):
    """
    Main CLI handler for running routines from templates.

    Args:
        args: Parsed command-line arguments
    """
    try:
        # Load template using smart detection
        from badger.utils import load_template_smart
        config = load_template_smart(args.template)

        # Create routine from template
        routine = Routine(**config)

        # Determine mode (default to GUI if neither specified)
        if args.headless:
            # Headless subprocess mode
            run_routine_headless(routine, auto_run=args.auto_run)
        else:
            # GUI mode (default)
            run_routine_gui(routine, auto_run=args.auto_run)

    except Exception as e:
        logger.error(f"Error running routine: {e}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
