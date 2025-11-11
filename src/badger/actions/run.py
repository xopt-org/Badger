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
    from multiprocessing import Process, Queue, Event, Pipe
    from badger.core_subprocess import run_routine_subprocess
    from badger.archive import save_tmp_run
    from badger.settings import init_settings

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

    # Set up subprocess communication (matching GUI architecture)
    # CRITICAL: Must create these BEFORE starting subprocess with 'spawn'
    data_queue = Queue()
    evaluate_queue = Pipe()
    stop_event = Event()
    pause_event = Event()
    wait_event = Event()
    config_path = init_settings()._instance.config_path

    # Start subprocess FIRST (matching GUI pattern)
    process = Process(
        target=run_routine_subprocess,
        args=(
            data_queue,
            evaluate_queue,
            stop_event,
            pause_event,
            wait_event,
            config_path,
        )
    )
    process.start()

    # Give subprocess time to start and reach wait_event.wait()
    # With 'spawn' on macOS, starting Python interpreter takes time
    time.sleep(3)

    # NOW calculate initial points and prepare data
    from badger.routine import calculate_initial_points
    import pandas as pd

    if routine.initial_points is None or len(routine.initial_points) == 0:
        init_points = calculate_initial_points(
            routine.initial_point_actions,
            routine.vocs,
            routine.environment,
        )
        try:
            init_points = pd.DataFrame(init_points)
        except (IndexError, ValueError):
            init_points = pd.DataFrame(init_points, index=[0])
        routine.initial_points = init_points

    # Record start time and save routine
    start_time = time.time()
    routine_filename = save_tmp_run(routine)

    # Prepare arguments to send to subprocess
    arg_dict = {
        "routine_id": routine.id if hasattr(routine, 'id') else None,
        "routine_filename": routine_filename,
        "routine_name": routine.name,
        "variable_ranges": routine.vocs.variables,
        "initial_points": routine.initial_points,
        "evaluate": True,
        "archive": True,
        "termination_condition": None,
        "start_time": start_time,
        "testing": False,
    }

    # NOW put data in queue (subprocess is already running and waiting)
    data_queue.put(arg_dict)

    # Signal subprocess to begin execution
    pause_event.set()  # Start unpaused
    wait_event.set()   # Signal subprocess to begin

    # Monitor progress
    print("Optimization started. Press Ctrl+C to stop.\n")
    iteration = 0
    last_data = None

    try:
        while process.is_alive():
            time.sleep(0.1)

            # Check for data from subprocess via evaluate_queue (Pipe)
            # This is how the GUI does it - evaluate_queue sends (data, generator) tuples
            if evaluate_queue[1].poll():
                while evaluate_queue[1].poll():
                    results = evaluate_queue[1].recv()
                    df = results[0]  # First element is the data DataFrame

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

            # Check for errors in data_queue
            if not data_queue.empty():
                try:
                    error_title, error_traceback = data_queue.get()
                    print(f"\n❌ Error: {error_title}")
                    print(error_traceback)
                    break
                except ValueError:
                    pass

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
