import multiprocessing
import pytest

def test_home_page_run_routine(qtbot):
    if multiprocessing.current_process().name != 'MainProcess':
        return  # Prevent execution in child processes

    # Import modules inside the function
    from PyQt5.QtCore import QEventLoop, QTimer
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
    QTimer.singleShot(1000, loop.quit)
    loop.exec_()

    home_page = main_page.home_page

    routines = [
        create_routine(),
        create_multiobjective_routine(),
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
        home_page.run_monitor.start(True)

        with qtbot.waitSignal(
            home_page.run_monitor.sig_progress, timeout=5000
        ) as blocker:
            pass

        assert blocker.signal_triggered

        while home_page.run_monitor.running:
            qtbot.wait(100)

        assert len(home_page.run_monitor.routine.data) == 3

    main_page.process_manager.close_proccesses()

if __name__ == '__main__':
    multiprocessing.set_start_method('spawn')
    pytest.main([__file__])
