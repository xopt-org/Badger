import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtCore import QEventLoop, QTimer
import multiprocessing
from badger.db import save_routine
import time 

@pytest.fixture(scope='session')
def init_multiprocessing():
    multiprocessing.set_start_method("fork", force=True)


def test_gui_main(qtbot, init_multiprocessing):
    from badger.gui.default.windows.main_window import BadgerMainWindow
    from badger.tests.utils import fix_db_path_issue

    fix_db_path_issue()

    window = BadgerMainWindow()

    while window.thread_list:
        loop = QEventLoop()
        QTimer.singleShot(1000, loop.quit)  # 1000 ms pause
        loop.exec_()
        time.sleep(1)
        print("test", print(window.thread_list))

    qtbot.addWidget(window)

    loop = QEventLoop()
    QTimer.singleShot(3000, loop.quit)  # 1000 ms pause
    loop.exec_()

    # Test new routine feature
    qtbot.mouseClick(window.home_page.btn_new, Qt.MouseButton.LeftButton)
    assert window.stacks.currentWidget().tabs.currentIndex() == 1


def test_close_main(qtbot, init_multiprocessing):
    from badger.gui.default.pages.home_page import BadgerHomePage
    from badger.gui.default.windows.main_window import BadgerMainWindow
    from badger.tests.utils import (
        create_routine,
        fix_db_path_issue,
    )

    fix_db_path_issue()

    main_page = BadgerMainWindow()

    loop = QEventLoop()
    QTimer.singleShot(3000, loop.quit)  # 1000 ms pause
    loop.exec_()

    home_page = main_page.home_page

    # test running routines w high level interface
    routine = create_routine()


    save_routine(routine)
    home_page.current_routine = routine
    home_page.run_monitor.testing = True
    home_page.run_monitor.termination_condition = {
        "tc_idx": 0,
        "max_eval": 3,
    }
    home_page.go_run(-1)
    # start run in a thread and wait some time for it to finish
    home_page.run_monitor.start(True)
        
    # assert we get the right result, ie. correct number of samples
    loop = QEventLoop()
    QTimer.singleShot(1000, loop.quit)  # 1000 ms pause
    loop.exec_()

    assert len(home_page.run_monitor.routine.data) == 3

    home_page.close()
    
    with pytest.raises(AttributeError):
        routine.environment


def test_close_main(qtbot, init_multiprocessing):
    from badger.gui.default.pages.home_page import BadgerHomePage
    from badger.gui.default.windows.main_window import BadgerMainWindow
    from badger.tests.utils import fix_db_path_issue, create_routine

    fix_db_path_issue()

    window = BadgerMainWindow()
    qtbot.addWidget(window)

    loop = QEventLoop()
    QTimer.singleShot(5000, loop.quit)  # 1000 ms pause
    loop.exec_()

    routine = create_routine()
    home_page = window.home_page
    home_page.current_routine = routine
    save_routine(routine)
    home_page.run_monitor.testing = True
    home_page.run_monitor.termination_condition = {
        "tc_idx": 0,
        "max_eval": 3,
    }
    home_page.go_run(-1)
    home_page.run_monitor.start(True)
   
    loop = QEventLoop()
    QTimer.singleShot(1000, loop.quit)  # 1000 ms pause
    loop.exec_()

    
    # Wait until the run is done
    
    #while home_page.run_monitor.running:
 
    # window.close()  # this action show release the env
    # So we expect an AttributeError here

    #with pytest.raises(AttributeError):
    #    routine.environment
