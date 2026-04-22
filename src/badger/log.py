import os
import datetime
import logging
import atexit

from logging.handlers import QueueHandler, QueueListener
from multiprocessing import Queue
from badger.settings import get_user_config_folder
from badger.settings import init_settings

logger = logging.getLogger(__name__)

"""
Logging system that allows subprocesses to send logs to a central listener
in the main process, writes logs to both logfile and the terminal.

We make use of the logging.handlers classes from the python standard library, mainly:
    QueueListener (in main process) — collects log records from a multiprocessing.Queue
    QueueHandler (in subprocesses) — sends log records to the main process queue

For example usage (in a simple context), see src/badger/tests/test_multiprocess_logging.py
"""


class LoggingManager:
    """
    Used to manage logging across multiple processes,
    one listener thread collects logs from all worker sub-processes via a queue.
    """

    def __init__(self):
        self.log_queue: Queue = None
        self.listener: QueueListener = None
        self.handlers = []

    def start_listener(self, log_filepath: str, log_level: str | int):
        """
        For use in main process to setup queue and start listening for logs from sub processes.

        args:
            log_filepath (str): Path to the log file
            log_level (str or int): Logging level
        """
        if isinstance(log_level, str):
            log_level = getattr(
                logging, log_level.upper(), logging.DEBUG
            )  # turns str into enum

        # Queue for sending all the logs to
        self.log_queue = Queue()

        self.handlers = []
        # File handler
        file_handler = logging.FileHandler(log_filepath, mode="a")
        file_formatter = logging.Formatter(
            "%(asctime)s - %(processName)-12s - %(levelname)-8s - %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(log_level)
        self.handlers.append(file_handler)

        # Terminal handler
        terminal_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            "%(asctime)s - %(processName)-12s - %(levelname)-8s - %(message)s"
        )
        terminal_handler.setFormatter(console_formatter)
        terminal_handler.setLevel(log_level)
        self.handlers.append(terminal_handler)

        # Start the queue listener (python std-library object) in a thread
        self.listener = QueueListener(
            self.log_queue, *self.handlers, respect_handler_level=True
        )  # '*' unpacks the array for us (unpacking operator)
        self.listener.start()

        logger.info(
            f"Centralized logging listener started with level {logging.getLevelName(log_level)}"
        )

    def stop_listener(self):
        if self.listener:
            self.listener.stop()
            logger.info("Main process logging listener stopped")

    def update_log_level(self, log_level: str | int):
        """
        Update log level in the handlers and logger objects in main process (only two handlers atm, terminal and file).
        This affects which level of logs (from any process) get written to the logfile.

        args:
            log_level (str or int): new logging level
        """
        if isinstance(log_level, str):
            log_level = getattr(logging, log_level.upper(), logging.DEBUG)

        for handler in self.handlers:
            handler.setLevel(log_level)

        # Updating the "badger" namespace logger,
        # ensures all badger.* loggers in main thread respect the new level
        badger_logger = logging.getLogger("badger")
        badger_logger.setLevel(log_level)

        # Update all existing child loggers too
        for name, logger_obj in logging.root.manager.loggerDict.items():
            if isinstance(logger_obj, logging.Logger) and name.startswith("badger"):
                logger_obj.setLevel(log_level)

        logger.info(
            f"Log level updated to {logging.getLevelName(log_level)} for badger namespace."
        )

    def update_logfile_path(self, new_logfile_path: str):
        """
        Update logfile path, so logs get written to a different file.

        Note that we can't change a handler's filepath, so instead need to create entirely new handler pointing
        to the new logfile path. Then we need to close out existing handler, and then restart
        the QueueListener while passing in the new handlers.
        """
        # Get the existing handler
        file_handler = None
        for h in self.handlers:
            if isinstance(h, logging.FileHandler):
                file_handler = h
                break

        # We want to keep using same formatter and loglevel
        formatter = file_handler.formatter
        log_level = file_handler.level

        # Stop the current QueueListener (should do before closing file-handler)
        if self.listener:
            self.listener.stop()

        # Close out the old handlers
        file_handler.close()
        self.handlers.remove(file_handler)

        # Create new handler pointing to new logfile
        new_file_handler = logging.FileHandler(new_logfile_path, mode="a")
        new_file_handler.setFormatter(formatter)
        new_file_handler.setLevel(log_level)
        self.handlers.append(new_file_handler)

        # Restart QueueListener, using new handlers
        self.listener = QueueListener(
            self.log_queue, *self.handlers, respect_handler_level=True
        )
        self.listener.start()

        logger.info(f"Logfile path updated to {new_logfile_path}")

    def get_logfile_name(self):
        """
        Get name of the logfile for today, which is in form of:
        "log_<month>_<day>.log"
        """
        today = datetime.date.today()
        log_filename = f"log_{today.year:04d}_{today.month:02d}_{today.day:02d}.log"
        return log_filename

    def get_queue(self) -> Queue:
        """Get the logging queue for use by subprocesses."""
        return self.log_queue

    def create_log_dir(self, log_dir: str):
        """
        Create the logs directory if it doesn't exist.

        args:
            log_dir: directory to potentially create.
        """
        # If not set, empty, or invalid, use default (/logs dir in root of repo)
        if log_dir is None:
            log_dir = "logs"

        # Expand user home directory if needed
        log_dir = os.path.expanduser(log_dir)

        # Create directory if it doesn't exist
        try:
            os.makedirs(log_dir, exist_ok=True)
        except PermissionError:
            # Fall back to user config folder if we can't create the directory
            logger.warning(f"Cannot create log directory {log_dir}, using default")
            log_dir = os.path.join(get_user_config_folder(), "logs")
            os.makedirs(log_dir, exist_ok=True)
        except FileExistsError:
            # Something with this name exists but it's not a directory
            logger.warning(f"{log_dir} exists but is not a directory, using default")
            log_dir = os.path.join(get_user_config_folder(), "logs")
            os.makedirs(log_dir, exist_ok=True)


def configure_process_logging(
    log_queue: Queue = None,
    logger_name: str = "badger",
    log_level: str = "DEBUG",
    process_name: str = None,
):
    """
    Configure logging in a process to send logs to the shared queue.
    This should be ran in all subprocesses b4 logging, and also in the main process where
    the QueueListener lives (since main process is a log producer too!).

    args:
        logger_name (str): Name of the logger (default: "badger")
        log_level (int or str): Logging level to set
        process_name (str): Custom process name to output in logs
    """
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper(), logging.DEBUG)

    # Set custom process name if provided
    if process_name:
        import multiprocessing as mp

        mp.current_process().name = process_name

    # Get top level logger for this namespace
    logger = logging.getLogger(logger_name)
    # Clear any existing handlers
    logger.handlers.clear()

    logger.propagate = False

    if log_queue is not None:
        # Add queue handler so logs get sent to queue in main process
        queue_handler = QueueHandler(log_queue)
        logger.addHandler(queue_handler)

    logger.setLevel(log_level)

    # Also set level for all child loggers in the namespace
    for name, logger_obj in logging.root.manager.loggerDict.items():
        if isinstance(logger_obj, logging.Logger) and name.startswith(logger_name):
            logger_obj.setLevel(log_level)

    logger.info(
        f"process logger configured with level {logging.getLevelName(log_level)}"
    )


def setup_logging(args):
    """
    Init Badger's multiprocess logging system
    """

    logging_manager = get_logging_manager()
    config_singleton = init_settings(args.config_filepath)

    # Log dir
    log_dir = config_singleton.read_value("BADGER_LOG_DIRECTORY")
    logging_manager.create_log_dir(log_dir)
    log_dir_expanded = os.path.expanduser(log_dir)

    # Daily log file
    logfile_name = logging_manager.get_logfile_name()
    logfile_path = os.path.join(log_dir_expanded, logfile_name)

    logging_manager.start_listener(
        log_filepath=str(logfile_path),
        log_level=args.log_level,
    )

    configure_process_logging(logging_manager.log_queue, log_level=args.log_level)

    # Prevent propagation to root
    badger_logger = logging.getLogger("badger")
    badger_logger.propagate = False

    # Ensure listener shuts down at exit
    atexit.register(
        lambda: logging_manager.listener and logging_manager.listener.stop()
    )


# Calling `from badger.log import get_logging_manager, configure_subprocess_logger` will execute this line,
# Since despite only specifying two functions to import, python still runs the whole file.
# And it only gets created once, the first time this file is imported.
_logging_manager = LoggingManager()


def get_logging_manager() -> LoggingManager:
    # Get global logging-manager instance.
    return _logging_manager
