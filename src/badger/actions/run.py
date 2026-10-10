"""
Runs an optimization routine from the command line and saves results.

The main function here is run_n_archive: it calls core.run_routine in a loop,
catches Ctrl-C (SIGINT) for pause/resume, periodically dumps data to the
archive, and logs interface channel values to disk.

Note: the CLI runner is deprecated — most users should use the GUI instead.
"""

import logging
import os
import signal
import sys
import time
from multiprocessing import Event, Pipe, Process, Queue

import pandas as pd
from pandas import DataFrame
from typing_extensions import deprecated

from badger.core import run_routine as run
from badger.core_subprocess import run_routine_subprocess
from badger.errors import BadgerLoadConfigError, BadgerRunTerminated
from badger.log import get_logging_manager
from badger.settings import init_settings
from badger.utils import curr_ts, load_template_file, load_template_string

logger = logging.getLogger(__name__)


def run_n_archive(
    routine, yes=False, save=False, verbose=2, sleep=0, flush_prompt=False
):
    try:
        from badger.archive import archive_run
    except Exception as e:  # noqa: BLE001 - import triggers config/plugin loading; report and exit
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
            print()  # start a new line
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
            except Exception:  # noqa: BLE001 - interface dump is best-effort
                logger.warning("Failed to dump interface logs")

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
    except Exception as e:  # noqa: BLE001 - CLI run boundary
        logger.error(e)

    # Save the run when at least one solution has been evaluated
    if len(routine.data):
        _run = archive_run(routine, storage["states"])
        # Try dump the interface logs
        try:
            path = _run["path"]
            filename = _run["filename"][:-4] + "pickle"
            routine.environment.interface.stop_recording(os.path.join(path, filename))
        except Exception:  # noqa: BLE001 - interface dump is best-effort
            logger.warning("Failed to dump interface logs")


@deprecated("The `badger run` command is deprecated. Please use the GUI.")
def run_routine(args):
    print(
        "This command is deprecated.\n"
        "Please use 'badger -g' to launch the Badger GUI "
        "and run an optimization."
    )


def run_routine_gui(routine, auto_run=False):
    """
    Launch ACR GUI with pre-loaded routine.

    Args:
        routine: Routine object to load
        auto_run: If True, automatically start optimization after loading
    """
    from badger.gui import launch_gui

    launch_gui(routine=routine, auto_run=auto_run)


def run_routine_headless(routine, auto_run=False):
    """
    Run routine in headless mode using subprocess.

    Args:
        routine: Routine object to run
        auto_run: If True, skip confirmation prompt
    """
    print(f"\n{'=' * 60}")
    print(f"Routine: {routine.name}")
    print(f"Environment: {routine.environment.name}")
    print(f"Generator: {routine.generator.name}")
    print(f"Variables: {list(routine.vocs.variables.keys())}")
    print(f"Objectives: {list(routine.vocs.objectives.keys())}")
    if routine.vocs.constraints:
        print(f"Constraints: {list(routine.vocs.constraints.keys())}")
    print(f"{'=' * 60}\n")

    # Ask for confirmation if not auto_run
    if not auto_run:
        try:
            response = input("Start optimization? [y/N]: ")
            if response.lower() != "y":
                print("Cancelled.")
                return
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return

    from badger.archive import save_tmp_run
    from badger.routine import calculate_initial_points

    # ------------------------------------------------------------------ #
    # Prepare all work before spawning — so the child is never left       #
    # blocked in wait_event.wait() due to a setup failure after start().  #
    # ------------------------------------------------------------------ #

    # Calculate initial points
    if routine.initial_points is None or len(routine.initial_points) == 0:
        init_points = calculate_initial_points(
            routine.initial_point_actions or [],
            routine.vocs,
            routine.environment,
        )
        try:
            init_points = pd.DataFrame(init_points)
        except (IndexError, ValueError):
            init_points = pd.DataFrame(init_points, index=[0])
        routine.initial_points = init_points

    start_time = time.time()
    routine_filename = save_tmp_run(routine)

    # Build the arg dict that will be fed to the subprocess via args_queue
    arg_dict = {
        "routine_id": routine.id if hasattr(routine, "id") else None,
        "routine_filename": routine_filename,
        "routine_name": routine.name,
        "variable_ranges": routine.vocs.variables,
        "initial_points": routine.initial_points,
        "evaluate": True,
        "archive": True,
        "termination_condition": None,
        "start_time": start_time,
        "testing": False,
        "run_data": False,
        "init_points": True,
    }

    # Set up subprocess communication channels
    args_queue = Queue()
    data_queue = Queue()
    evaluate_queue = Pipe()
    stop_event = Event()
    pause_event = Event()
    wait_event = Event()
    config_path = init_settings()._instance.config_path
    logging_manager = get_logging_manager()
    log_queue = logging_manager.get_queue()
    dialog_action_queue = Queue()

    process = Process(
        target=run_routine_subprocess,
        args=(
            args_queue,
            data_queue,
            evaluate_queue,
            stop_event,
            pause_event,
            wait_event,
            config_path,
            log_queue,
            dialog_action_queue,
        ),
    )

    # Storage for signal handler state — initialised before the handler is
    # installed so the handler closure always has a valid reference.
    storage = {"paused": False, "should_exit": False}

    def sigint_handler(*args):
        """Signal handler for Ctrl+C - sets pause flag or raises to exit."""
        if storage["paused"]:
            # Second Ctrl+C while paused — interrupt input() and exit.
            print()  # new line
            storage["should_exit"] = True
            raise KeyboardInterrupt
        else:
            # First Ctrl+C — request pause.
            storage["paused"] = True

    # Capture the current handler *before* installing ours so we can
    # restore it unconditionally in the finally block below.
    prev_sigint = signal.signal(signal.SIGINT, sigint_handler)

    process.start()

    # give subprocess time to start and reach wait_event.wait()
    time.sleep(3)

    iteration = 0

    # Accumulate subprocess error messages; checked after full shutdown so
    # that errors queued just before the child exits are not missed.
    errors: list[str] = []

    try:
        # Feed work to the subprocess and release it
        args_queue.put(arg_dict)
        pause_event.set()  # Start unpaused
        wait_event.set()  # Signal subprocess to begin

        print("Optimization started. Press Ctrl+C to pause.\n")

        # Main monitoring loop
        while process.is_alive() and not storage["should_exit"]:
            time.sleep(0.1)

            # Handle pause/resume
            if storage["paused"]:
                pause_event.clear()  # Pause subprocess
                print()  # new line
                try:
                    res = input(
                        "Optimization paused. Press Enter to resume or Ctrl+C to terminate: "
                    )
                    while res != "":
                        sys.stdout.write("\033[F")  # Move cursor up to erase line
                        res = input(
                            "Invalid choice. Press Enter to resume or Ctrl+C to terminate: "
                        )
                except KeyboardInterrupt:
                    # Ctrl+C during input — sigint_handler already set should_exit.
                    pass

                if storage["should_exit"]:
                    print("\nStopping optimization...")
                    stop_event.set()
                    break

                print("Resuming optimization...\n")
                storage["paused"] = False
                pause_event.set()

            # Drain results from the subprocess
            if evaluate_queue[1].poll():
                while evaluate_queue[1].poll():
                    results = evaluate_queue[1].recv()
                    df = results[0]
                    iteration = max(iteration, len(df))

            # Collect errors reported by the subprocess; set stop_event and
            # break so teardown runs, but keep the message for later reporting.
            if not data_queue.empty():
                msg = data_queue.get()
                if isinstance(msg, dict):
                    errors.append(
                        f"{msg.get('title', 'Unknown error')}\n{msg.get('traceback', '')}"
                    )
                else:
                    error_title, error_traceback = msg
                    errors.append(f"{error_title}\n{error_traceback}")
                stop_event.set()
                break

    finally:
        # Always stop the child and restore the caller's signal handler,
        # regardless of whether we exit normally, via an exception, or Ctrl+C.
        stop_event.set()
        signal.signal(signal.SIGINT, prev_sigint)

        process.join(timeout=5)
        if process.is_alive():
            process.terminate()
            process.join()

    # ------------------------------------------------------------------ #
    # Post-shutdown error collection                                       #
    # ------------------------------------------------------------------ #

    # Drain any remaining items from evaluate_queue
    while evaluate_queue[1].poll():
        try:
            results = evaluate_queue[1].recv()
            df = results[0]
            iteration = max(iteration, len(df))
        except Exception:  # noqa: BLE001
            break

    # Drain errors that arrived just before the child exited — these can be
    # missed by the is_alive() guard in the monitoring loop above.
    while not data_queue.empty():
        try:
            msg = data_queue.get_nowait()
            if isinstance(msg, dict):
                errors.append(
                    f"{msg.get('title', 'Unknown error')}\n{msg.get('traceback', '')}"
                )
            else:
                error_title, error_traceback = msg
                errors.append(f"{error_title}\n{error_traceback}")
        except Exception:  # noqa: BLE001 - queue may be closed/empty by now
            break

    # A non-zero exit code means the child crashed without sending an error
    # message (e.g. unhandled exception, OOM kill, or external signal).
    exitcode = process.exitcode
    if exitcode not in (0, None) and not errors:
        errors.append(
            f"Subprocess exited with non-zero exit code {exitcode}. "
            "Check logs for details."
        )

    # Print final status
    elapsed = time.time() - start_time
    print(f"\n{'=' * 60}")
    if errors:
        print(
            f"Optimization FAILED after {elapsed:.2f}s ({iteration} iteration(s) completed)"
        )
    else:
        print(f"Optimization completed in {elapsed:.2f}s")
    print(f"Total iterations: {iteration}")
    print(f"{'=' * 60}\n")

    # Propagate failures so run_routine_cli exits with a non-zero status.
    if errors:
        formatted = "\n\n".join(errors)
        raise RuntimeError(f"Headless optimization failed:\n{formatted}")


def run_routine_cli(args):
    """
    Main CLI handler for running routines from templates.

    Args:
        args: Parsed command-line arguments
    """
    try:
        if args.template_file == "" and args.template_string == "":
            raise BadgerLoadConfigError("Template input cannot be empty")

        if args.template_file is not None:
            config = load_template_file(args.template_file)
        else:
            config = load_template_string(args.template_string)

        environment_config = config.get("environment")
        if isinstance(environment_config, dict) and isinstance(
            environment_config.get("params"), dict
        ):
            environment_config.update(environment_config.pop("params"))

        from badger.routine import Routine

        routine = Routine(**config)

        if args.headless:
            run_routine_headless(routine, auto_run=args.auto_run)
        else:
            # gui mode (default mode)
            run_routine_gui(routine, auto_run=args.auto_run)

    except Exception as e:  # noqa: BLE001
        logger.error(f"Error running routine: {e}")
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
