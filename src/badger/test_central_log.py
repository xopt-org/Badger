# Test script to verify everything works:

import logging
import time
from multiprocessing import Process, Queue
from badger.log import get_logging_manager, configure_subprocess_logger

logger = logging.getLogger("badger")

def test_subprocess(log_queue):
    """Simulates your optimization subprocess"""
    configure_subprocess_logger(
        log_queue=log_queue,
        logger_name="badger",
        log_level="DEBUG",
        process_name="TestWorker"
    )
    
    sub_logger = logging.getLogger("badger.test")
    
    for i in range(5):
        sub_logger.debug(f"Debug message {i} from subprocess")
        sub_logger.info(f"Info message {i} from subprocess")
        time.sleep(0.5)

def test_centralized_logging():
    # Start centralized logging
    logging_manager = get_logging_manager()
    logging_manager.start_listener(
        log_filepath="test_multiprocess.log",
        level="DEBUG"
    )
    
    logger.info("Main process: Starting test")
    
    # Start subprocess
    log_queue = logging_manager.get_queue()
    p = Process(target=test_subprocess, args=(log_queue,))
    p.start()
    
    # Main process continues logging
    for i in range(5):
        logger.info(f"Main process message {i}")
        time.sleep(0.3)
    
    p.join()
    
    logger.info("Main process: Test complete")
    
    # Stop logging
    logging_manager.stop_listener()
    
    print("\n✅ Check test_multiprocess.log - you should see interleaved messages from both processes!")

if __name__ == "__main__":
    test_centralized_logging()