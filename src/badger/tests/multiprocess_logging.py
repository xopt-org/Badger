import logging
import time
from multiprocessing import Process
from badger.log import get_logging_manager, configure_process_logging

"""
Note: this test does not have "test" in the filename so pytest does not discover it when running tests in a group.
This is b/c the logging code doesn't seem to play nice with pytest and causes
it to hang for unknown reasons. This test still runs well if executed directly: `pytest multiprocess_logging.py`

Testing of the code used for managing logging across Badger's multiple processes,
including changing the loglevel and logfile path in the main process and having the
subprocesses update accordingly.

Here we test the functionality of the logging code by using a simple main and subprocess, which mimickes the setup
in the real Badger codebase. So if this simplified setup breaks, we can assume Badger's real logging
is likely broken aswell. Testing should eventually be expanded to test the logging code from a Badger users perspective.
"""


def simple_subprocess(log_queue):
    configure_process_logging(log_queue=log_queue, log_level="DEBUG")

    sub_logger = logging.getLogger("badger.subprocess")

    for i in range(5):
        sub_logger.debug(f"debug message {i} from subprocess")
        time.sleep(0.5)


def test_multiprocessed_logging(tmp_path):
    # deleted after each run
    log_filepath_1 = tmp_path / "test_multiprocess_1.log"
    log_filepath_2 = tmp_path / "test_multiprocess_2.log"

    # start main process logging
    logging_manager = get_logging_manager()
    logging_manager.start_listener(log_filepath=str(log_filepath_1), log_level="DEBUG")

    # configure main process logger to use the shared queue
    log_queue = logging_manager.get_queue()
    configure_process_logging(log_queue=log_queue, log_level="DEBUG")

    main_logger = logging.getLogger("badger.main")
    main_logger.info("main process: starting test")

    # start subprocess
    p = Process(target=simple_subprocess, args=(log_queue,))
    p.start()

    # main process continues logging
    for i in range(3):
        main_logger.info(f"main process message {i}")
        time.sleep(0.3)

    # change log level across all processes
    logging_manager.update_log_level("ERROR")
    main_logger.debug("This DEBUG message should NOT appear")
    main_logger.error("This ERROR message should appear")

    # change logfile path across all processes
    logging_manager.update_logfile_path(str(log_filepath_2))

    main_logger.error("Logging to new logfile now!")
    main_logger.debug("This DEBUG message should NOT appear")
    main_logger.error("This ERROR message should appear")

    p.join()
    assert p.exitcode == 0, (
        f"subprocess crashed with exit code {p.exitcode}. "
        "check subprocess func for errors."
    )

    # stop logging
    logging_manager.stop_listener()

    assert log_filepath_1.exists()
    assert log_filepath_1.stat().st_size > 0
    with open(log_filepath_1, "r") as f:
        print("\n====== log_filepath_1 contents ======\n")
        print(f.read())
        print("==============================")

    assert log_filepath_2.exists()
    assert log_filepath_2.stat().st_size > 0
    with open(log_filepath_2, "r") as f:
        print("\n====== log_filepath_2 contents ======\n")
        print(f.read())
        print("==============================")

    log_filepath_1_text = log_filepath_1.read_text()
    log_filepath_1_text_lines = log_filepath_1_text.splitlines()

    # check main process msgs appear
    assert any("main process message 0" in line for line in log_filepath_1_text_lines)
    assert any("main process message 1" in line for line in log_filepath_1_text_lines)
    assert any("main process message 2" in line for line in log_filepath_1_text_lines)

    # check subprocess messages appear
    assert any(
        "debug message 0 from subprocess" in line for line in log_filepath_1_text_lines
    )

    # check loglevel change worked
    assert "This DEBUG message should NOT appear" not in log_filepath_1_text
    assert "This ERROR message should appear" in log_filepath_1_text

    log_filepath_2_text = log_filepath_2.read_text()
    log_filepath_2_text_lines = log_filepath_2_text.splitlines()
    assert any(
        "Logging to new logfile now!" in line for line in log_filepath_2_text_lines
    )
    assert "This DEBUG message should NOT appear" not in log_filepath_2_text


if __name__ == "__main__":
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        test_multiprocessed_logging(Path(tmpdir))
