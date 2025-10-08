import logging
from logging.config import dictConfig
from logging.handlers import QueueHandler, QueueListener
from badger.utils import merge_params
from typing import Optional
logger = logging.getLogger(__name__)
from multiprocessing import Queue

'''
def set_log_level(level):
    loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    for logger in loggers:
        logger.setLevel(level)
'''

def init_logger(logger_obj, log_filepath, level):
    """
    Init a named logger with handlers to log file and terminal.

    Args:
        logger_obj (logging.Logger): Logger to configure.
        log_filepath (str): Path to log file.
        level (str): Logging level.
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.DEBUG)

    logger_obj.setLevel(level)

    # prevent logging messages from being propagated to root
    # logger_obj.propagate = False

    # file handler
    file_handler = logging.FileHandler(log_filepath, mode='a')
    # console handler
    stream_handler = logging.StreamHandler()

    # formatting
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    stream_handler.setFormatter(formatter)

    logger_obj.addHandler(file_handler)
    logger_obj.addHandler(stream_handler)

def set_log_level(level, project_namespace="badger"):
    """
    Set logging level for all loggers in badger only.

    Args:
        level (str): logging level
        project_namespace (str): the root name of your project loggers
    """
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.DEBUG)

    root_logger = logging.getLogger(project_namespace)
    root_logger.setLevel(level)

    # iterate all existing loggers, only update those in your namespace
    for name, logger_obj in logging.root.manager.loggerDict.items():
        if isinstance(logger_obj, logging.Logger) and name.startswith(project_namespace):
            logger.info(f"Setting logger {logger_obj.name} to level {logging.getLevelName(level)}")
            logger_obj.setLevel(level)

    # optionally also update handlers on root logger
    for handler in root_logger.handlers:
        handler.setLevel(level)


# ============ NEW: Centralized Multiprocessing Logging ============

class CentralizedLoggingManager:
    """
    Manages centralized logging for multiprocessing applications.
    One listener thread collects logs from all worker processes via a queue.
    """
    
    def __init__(self):
        self.log_queue: Optional[Queue] = None
        self.listener: Optional[QueueListener] = None
        self.handlers = []
        
    def start_listener(self, log_filepath: str, level, gui_callback=None):
        """
        Start the centralized logging listener.
        
        Args:
            log_filepath (str): Path to the log file
            level (str or int): Logging level
            gui_callback (callable, optional): Function to call with log messages for GUI display
        """
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.DEBUG)
            
        # Create queue for log records
        self.log_queue = Queue()
        
        # Clear old handlers
        self.handlers = []
        
        # File handler
        file_handler = logging.FileHandler(log_filepath, mode='a')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(processName)-12s - %(name)-20s - %(levelname)-8s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(level)
        self.handlers.append(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '%(asctime)s - %(processName)-12s - %(levelname)-8s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        console_handler.setLevel(level)
        self.handlers.append(console_handler)
        
        # GUI handler (optional)
        if gui_callback:
            class GUIHandler(logging.Handler):
                def emit(self, record):
                    try:
                        msg = self.format(record)
                        gui_callback(msg)
                    except Exception:
                        self.handleError(record)
            
            gui_handler = GUIHandler()
            gui_handler.setFormatter(console_formatter)
            gui_handler.setLevel(level)
            self.handlers.append(gui_handler)
        
        # Start the queue listener in a thread
        self.listener = QueueListener(
            self.log_queue, 
            *self.handlers, 
            respect_handler_level=True
        )
        self.listener.start()
        
        logger.info(f"Centralized logging listener started with level {logging.getLevelName(level)}")
        
    def stop_listener(self):
        """Stop the logging listener."""
        if self.listener:
            self.listener.stop()
            logger.info("Centralized logging listener stopped")
            
    def update_log_level(self, level):
        """
        Update the log level for all handlers.
        
        Args:
            level (str or int): New logging level
        """
        if isinstance(level, str):
            level = getattr(logging, level.upper(), logging.DEBUG)
            
        for handler in self.handlers:
            handler.setLevel(level)
            
        logger.info(f"Log level updated to {logging.getLevelName(level)} for all handlers")
        
    def get_queue(self) -> Optional[Queue]:
        """Get the logging queue for use by subprocesses."""
        return self.log_queue


def configure_subprocess_logger(
    log_queue: Optional[Queue] = None,
    logger_name: str = "badger",
    log_level=logging.DEBUG,
    process_name: Optional[str] = None
):
    """
    Configure logging for a subprocess to send logs to the central queue.
    
    Args:
        log_queue (Queue): The queue to send log records to
        logger_name (str): Name of the logger (default: "badger")
        log_level (int or str): Logging level
        process_name (str, optional): Custom process name for logs
    """
    if isinstance(log_level, str):
        log_level = getattr(logging, log_level.upper(), logging.DEBUG)
    
    # Set custom process name if provided
    if process_name:
        import multiprocessing as mp
        mp.current_process().name = process_name
    
    # Get the root logger for this namespace
    root_logger = logging.getLogger(logger_name)
    
    # Clear any existing handlers
    root_logger.handlers.clear()
    
    if log_queue is not None:
        # Add queue handler to send to central listener
        queue_handler = QueueHandler(log_queue)
        root_logger.addHandler(queue_handler)
    else:
        # Fallback to null handler if no queue provided
        root_logger.addHandler(logging.NullHandler())
    
    root_logger.setLevel(log_level)
    
    # Also set level for all child loggers in the namespace
    for name, logger_obj in logging.root.manager.loggerDict.items():
        if isinstance(logger_obj, logging.Logger) and name.startswith(logger_name):
            logger_obj.setLevel(log_level)
    
    root_logger.info(f"Subprocess logger configured with level {logging.getLevelName(log_level)}")


# Global instance
_logging_manager = CentralizedLoggingManager()


def get_logging_manager() -> CentralizedLoggingManager:
    """Get the global logging manager instance."""
    return _logging_manager