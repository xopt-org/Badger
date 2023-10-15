import pandas as pd
import pytest
from PyQt5.QtCore import Qt

from badger.errors import BadgerRoutineError


def test_routine_page_init(qtbot):
    from badger.gui.default.components.routine_page import BadgerRoutinePage

    window = BadgerRoutinePage()

    window.show()
    qtbot.addWidget(window)


def test_routine_generation(qtbot):
    # test if a simple routine can be created
    from badger.gui.default.components.routine_page import BadgerRoutinePage

    window = BadgerRoutinePage()

    qtbot.addWidget(window)

    # test without anything selected
    with pytest.raises(BadgerRoutineError):
        window._compose_routine()

    # add algorithm -- still should raise error for no environment
    qtbot.keyClicks(window.algo_box.cb, "upper_confidence_bound")
    with pytest.raises(BadgerRoutineError):
        window._compose_routine()

    # finally add the test environment
    qtbot.keyClicks(window.env_box.cb, "test")

    # click checkbox to select vars objectives
    window.env_box.var_table.cellWidget(0, 0).setChecked(True)
    assert window.env_box.var_table.export_variables() == {"x0": [-1, 1]}

    window.env_box.obj_table.cellWidget(0, 0).setChecked(True)
    assert window.env_box.obj_table.export_objectives() == {"f": "MINIMIZE"}

    routine = window._compose_routine()
    assert routine.vocs.variables == {"x0": [-1, 1]}
    assert routine.vocs.objectives == {"f": "MINIMIZE"}
    assert routine.initial_points.empty

    # test routine generation with fake current values selected
    qtbot.mouseClick(window.env_box.btn_add_curr, Qt.LeftButton)
    routine = window._compose_routine()
    assert routine.initial_points.to_dict() == pd.DataFrame({"x0": 0},
                                                            index=[0]).to_dict()


def test_initial_points(qtbot):
    # test to make sure initial points widget works properly
    from badger.gui.default.components.routine_page import BadgerRoutinePage

    window = BadgerRoutinePage()
    qtbot.addWidget(window)

    qtbot.keyClicks(window.env_box.cb, "test")
    window.env_box.var_table.cellWidget(0, 0).setChecked(True)
    window.env_box.var_table.cellWidget(1, 0).setChecked(True)
    window.env_box.var_table.cellWidget(2, 0).setChecked(True)

    assert window.env_box.init_table.horizontalHeader().count() == 3



