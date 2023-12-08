def test_home_page_run_routine(qtbot):
    from badger.gui.default.pages.home_page import BadgerHomePage

    from badger.tests.utils import (
        create_multiobjective_routine,
        create_routine,
        create_routine_turbo,
        fix_db_path_issue,
    )

    fix_db_path_issue()
    home_page = BadgerHomePage()

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
        qtbot.wait(1000)

        # assert we get the right result, ie. correct number of samples
        assert len(home_page.run_monitor.routine_runner.routine.data) == 3
