import multiprocessing

import pytest
from PyQt5.QtCore import QEventLoop, QTimer


@pytest.fixture(scope="session")
def init_multiprocessing():
    multiprocessing.set_start_method("fork", force=True)


def test_home_page_run_routine(qtbot, init_multiprocessing):
    from badger.db import save_routine
    from badger.gui.default.windows.main_window import BadgerMainWindow
    from badger.tests.utils import (
        create_multiobjective_routine,
        create_routine,
        fix_db_path_issue,
    )

    fix_db_path_issue()

    main_page = BadgerMainWindow()

    loop = QEventLoop()
    QTimer.singleShot(1000, loop.quit)  # 1000 ms pause
    loop.exec_()

    home_page = main_page.home_page
    # test running routines w high level interface
    routines = [
        create_routine(),
        create_multiobjective_routine(),
        # create_routine_turbo(),
    ]

    for ele in routines:
        save_routine(ele)
        home_page.current_routine = ele
        home_page.run_monitor.testing = True
        home_page.run_monitor.termination_condition = {
            "tc_idx": 0,
            "max_eval": 3,
        }
        home_page.go_run(-1)
        # start run in a thread and wait some time for it to finish
        home_page.run_monitor.start(True)

        with qtbot.waitSignal(
            home_page.run_monitor.sig_progress, timeout=1000
        ) as blocker:
            pass

        assert blocker.signal_triggered

        # Wait until the run is done
        while home_page.run_monitor.running:
            qtbot.wait(100)

        # assert we get the right result, ie. correct number of samples
        assert len(home_page.run_monitor.routine.data) == 3

    main_page.process_manager.close_proccesses()
