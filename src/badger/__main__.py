import os
import argparse
import atexit
import logging

from badger.actions import show_info
from badger.actions.doctor import self_check
from badger.actions.routine import show_routine
from badger.actions.generator import show_generator
from badger.actions.env import show_env
from badger.actions.install import plugin_install
from badger.actions.uninstall import plugin_remove
from badger.actions.intf import show_intf
from badger.actions.config import config_settings
from badger.settings import init_settings
from badger.log import get_logging_manager

logger = logging.getLogger("badger")


def main():
    # Create the top-level parser
    parser = argparse.ArgumentParser(description="Badger the optimizer")
    parser.add_argument("-g", "--gui", action="store_true", help="launch the GUI")
    parser.add_argument(
        "-ga", "--gui-acr", action="store_true", help="launch the GUI for ACR"
    )

    parser.add_argument(
        "-l",
        "--log_level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="WARNING",
        const="WARNING",
        nargs="?",
        help="Set the logging level",
    )

    parser.add_argument(
        "-cf",
        "--config_filepath",
        type=str,
        default=None,
        help="Path to the config file",
    )
    parser.set_defaults(func=show_info)
    subparsers = parser.add_subparsers(help="Badger commands help")

    # Parser for the 'doctor' command
    parser_doctor = subparsers.add_parser("doctor", help="Badger status self-check")
    parser_doctor.add_argument(
        "-r", "--reset", action="store_true", help="reset Badger to factory settings"
    )
    parser_doctor.set_defaults(func=self_check)

    # Parser for the 'routine' command
    parser_routine = subparsers.add_parser("routine", help="Badger routines")
    parser_routine.add_argument("routine_name", nargs="?", type=str, default=None)
    parser_routine.add_argument(
        "-r", "--run", action="store_true", help="run the routine"
    )
    parser_routine.add_argument(
        "-y", "--yes", action="store_true", help="run the routine without confirmation"
    )
    parser_routine.add_argument(
        "-v",
        "--verbose",
        type=int,
        choices=[0, 1, 2],
        default=2,
        const=2,
        nargs="?",
        help="verbose level of optimization progress",
    )
    parser_routine.set_defaults(func=show_routine)

    # Parser for the 'generator' command
    parser_generator = subparsers.add_parser("generator", help="Badger generators")
    parser_generator.add_argument("generator_name", nargs="?", type=str, default=None)
    parser_generator.set_defaults(func=show_generator)

    # Parser for the 'intf' command
    parser_intf = subparsers.add_parser("intf", help="Badger interfaces")
    parser_intf.add_argument("intf_name", nargs="?", type=str, default=None)
    parser_intf.set_defaults(func=show_intf)

    # Parser for the 'env' command
    parser_env = subparsers.add_parser("env", help="Badger environments")
    parser_env.add_argument("env_name", nargs="?", type=str, default=None)
    parser_env.set_defaults(func=show_env)

    # Parser for the 'install' command
    parser_inst = subparsers.add_parser("install", help="Badger install plugin")
    parser_inst.add_argument("plugin_type", nargs="?", type=str, default=None)
    parser_inst.add_argument("plugin_specific", nargs="?", type=str, default=None)
    parser_inst.set_defaults(func=plugin_install)

    # Parser for the 'remove' command
    parser_remove = subparsers.add_parser("remove", help="Badger remove plugin")
    parser_remove.add_argument("plugin_type", nargs="?", type=str, default=None)
    parser_remove.add_argument("plugin_specific", nargs="?", type=str, default=None)
    parser_remove.set_defaults(func=plugin_remove)

    # Parser for the 'run' command
    parser_run = subparsers.add_parser("run", help="run routines")
    parser_run.add_argument("-a", "--generator", required=True, help="generator to use")
    parser_run.add_argument(
        "-ap", "--generator_params", help="parameters for the generator"
    )
    parser_run.add_argument("-e", "--env", required=True, help="environment to use")
    parser_run.add_argument(
        "-ep", "--env_params", help="parameters for the environment"
    )
    parser_run.add_argument(
        "-c", "--config", required=True, help="config for the routine"
    )
    parser_run.add_argument(
        "-s", "--save", nargs="?", const="", help="the routine name to be saved"
    )
    parser_run.add_argument(
        "-y", "--yes", action="store_true", help="run the routine without confirmation"
    )
    parser_run.add_argument(
        "-v",
        "--verbose",
        type=int,
        choices=[0, 1, 2],
        default=2,
        const=2,
        nargs="?",
        help="verbose level of optimization progress",
    )

    # Parser for the 'config' command
    parser_config = subparsers.add_parser("config", help="Badger configurations")
    parser_config.add_argument("key", nargs="?", type=str, default=None)
    parser_config.set_defaults(func=config_settings)

    args = parser.parse_args()

    # setup mutliprocess logging
    config_singleton = init_settings(args.config_filepath)

    logging_manager = get_logging_manager()

    log_dir = config_singleton.read_value("BADGER_LOG_DIRECTORY")
    logging_manager.create_log_dir(log_dir)
    log_dir_expanded_path = os.path.expanduser(log_dir)
    log_filename = logging_manager.get_logfile_name()
    new_logfile_path = os.path.join(log_dir_expanded_path, log_filename)
    logging_manager.start_listener(
        log_filepath=str(new_logfile_path), log_level=args.log_level
    )
    # configure main process logger to use a shared queue, which subprocesses will send their log msgs to
    logging_manager.configure_process_logging(log_level=args.log_level)

    # Prevent propagation to root logger
    badger_logger = logging.getLogger("badger")
    badger_logger.propagate = False

    # cleanup QueueListener thread
    atexit.register(
        lambda: logging_manager.listener and logging_manager.listener.stop()
    )

    args.func(args)


if __name__ == "__main__":
    main()
