import logging
from logging.handlers import QueueHandler, QueueListener
from multiprocessing import Queue

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
        Update log level in the handlers (only two handlers atm, terminal and file).
        This affects which level of logs (from any process) get written to the logfile.

        args:
            log_level (str or int): new logging level
        """
        if isinstance(log_level, str):
            log_level = getattr(logging, log_level.upper(), logging.DEBUG)

        for handler in self.handlers:
            handler.setLevel(log_level)

        # Updating the "badger" namespace logger
        # This ensures all badger.* loggers respect the new level
        badger_logger = logging.getLogger("badger")
        badger_logger.setLevel(log_level)

        # Update all existing child loggers in badger namespace
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

        # Stop the current QueueListener
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

    def get_queue(self) -> Queue:
        """Get the logging queue for use by subprocesses."""
        return self.log_queue


def configure_process_logging(
    log_queue: Queue = None,
    logger_name: str = "badger",
    log_level=logging.DEBUG,
    process_name: str = None,
):
    """
    Configure logging in processes to send logs to the central queue.

    args:
        log_queue (Queue): Queue to send log records to
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
        f"Subprocess logger configured with level {logging.getLevelName(log_level)}"
    )


# Calling `from badger.log import get_logging_manager, configure_subprocess_logger` will execute this line,
# Since despite only specifying two functions to import, python still runs the whole file.
# And it only gets created once, the first time this file is imported.
_logging_manager = LoggingManager()


def get_logging_manager() -> LoggingManager:
    # Get global logging-manager instance.
    return _logging_manager
