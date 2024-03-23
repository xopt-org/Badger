import pytest
from badger.gui.default.components.process_manager import processManager  

@pytest.fixture
def process_manager():
    return processManager()

'''
def test_home_page_run_routine(process_manager, qtbot):
    from badger.gui.default.pages.home_page import BadgerHomePage
    from badger.gui.default.windows.main_window import BadgerMainWindow
    from badger.tests.utils import (
        create_multiobjective_routine,
        create_routine,
        create_routine_turbo,
        fix_db_path_issue,
    )

    process_manager
    print(process_manager, "test")
    fix_db_path_issue()

    main_page = BadgerMainWindow()
    home_page = main_page.home_page

    # test running routines w high level interface
    routines = [
        create_routine(),
        create_multiobjective_routine(),
        create_routine_turbo(),
    ]
    for ele in routines:
        home_page.current_routine = ele
        home_page.run_monitor.testing = True
        home_page.run_monitor.termination_condition = {
            "tc_idx": 0,
            "max_eval": 3,
        }
        home_page.go_run(-1)
        # start run in a thread and wait some time for it to finish
        home_page.run_monitor.start(True)
        
        with qtbot.waitSignal(home_page.run_monitor.sig_progress, timeout=1000) as blocker:
            pass

        assert blocker.signal_triggered

        # assert we get the right result, ie. correct number of samples
        assert len(home_page.run_monitor.routine.data) == 3

'''
