import pandas as pd
import pytest
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication

from badger.errors import BadgerRoutineError
from badger.tests.utils import create_routine


def test_routine_page_init(qtbot):
    from badger.gui.default.components.routine_page import BadgerRoutinePage

    window = BadgerRoutinePage()

    qtbot.addWidget(window)


def test_routine_generation(qtbot):
    # test if a simple routine can be created
    from badger.gui.default.components.routine_page import BadgerRoutinePage
    window = BadgerRoutinePage()
    qtbot.addWidget(window)

    # test without anything selected
    with pytest.raises(BadgerRoutineError):
        window._compose_routine()

    # add generator -- still should raise error for no environment
    qtbot.keyClicks(window.generator_box.cb, "expected_improvement")
    with pytest.raises(BadgerRoutineError):
        window._compose_routine()

    # finally add the test environment
    qtbot.keyClicks(window.env_box.cb, "test")

    # click checkbox to select vars/objectives
    window.env_box.var_table.cellWidget(0, 0).setChecked(True)
    assert window.env_box.var_table.export_variables() == {"x0": [-1, 1]}

    window.env_box.obj_table.cellWidget(0, 0).setChecked(True)
    assert window.env_box.obj_table.export_objectives() == {"f": "MINIMIZE"}

    routine = window._compose_routine()
    assert routine.vocs.variables == {"x0": [-1, 1]}
    assert routine.vocs.objectives == {"f": "MINIMIZE"}
    assert routine.initial_points.empty


def test_initial_points(qtbot):
    # test to make sure initial points widget works properly
    from badger.gui.default.components.routine_page import BadgerRoutinePage

    window = BadgerRoutinePage()
    qtbot.addWidget(window)

    qtbot.keyClicks(window.env_box.cb, "test")
    qtbot.keyClicks(window.generator_box.cb, "random")

    window.env_box.var_table.cellWidget(0, 0).setChecked(True)
    window.env_box.var_table.cellWidget(1, 0).setChecked(True)
    window.env_box.var_table.cellWidget(2, 0).setChecked(True)

    assert window.env_box.init_table.horizontalHeader().count() == 3

    # test routine generation with fake current values selected
    qtbot.mouseClick(window.env_box.btn_add_curr, Qt.LeftButton)
    routine = window._compose_routine()
    assert routine.initial_points.to_dict() == pd.DataFrame(
        {"x0": 0, "x1": 0, "x2": 0}, index=[0]).to_dict()


def test_ui_update(qtbot):
    # test to make sure initial points widget works properly
    from badger.gui.default.components.routine_page import BadgerRoutinePage

    window = BadgerRoutinePage()

    # test with none
    window.refresh_ui()

    routine = create_routine()
    window.refresh_ui(routine)

    assert window.generator_box.edit.toPlainText() == "{}\n"


def test_constraints(qtbot):
    # test if a simple routine can be created
    from badger.gui.default.components.routine_page import BadgerRoutinePage
    window = BadgerRoutinePage()
    qtbot.addWidget(window)

    qtbot.keyClicks(window.generator_box.cb, "expected_improvement")
    qtbot.keyClicks(window.env_box.cb, "test")

    # click checkbox to select vars/objectives
    window.env_box.var_table.cellWidget(0, 0).setChecked(True)
    window.env_box.obj_table.cellWidget(0, 0).setChecked(True)
    # Select constraint
    qtbot.mouseClick(window.env_box.btn_add_con, Qt.MouseButton.LeftButton)
    con_item = window.env_box.list_con.item(0)
    con_widget = window.env_box.list_con.itemWidget(con_item)
    qtbot.keyClicks(con_widget.cb_obs, "c")
    con_widget.check_crit.setChecked(True)

    routine = window._compose_routine()
    assert routine.vocs.constraints == {"c": ["GREATER_THAN", 0]}
    assert routine.critical_constraint_names == ["c"]


def test_observables(qtbot):
    # test if a simple routine can be created
    from badger.gui.default.components.routine_page import BadgerRoutinePage
    window = BadgerRoutinePage()
    qtbot.addWidget(window)

    qtbot.keyClicks(window.generator_box.cb, "expected_improvement")
    qtbot.keyClicks(window.env_box.cb, "test")

    # click checkbox to select vars/objectives
    window.env_box.var_table.cellWidget(0, 0).setChecked(True)
    window.env_box.obj_table.cellWidget(0, 0).setChecked(True)
    # Select observable
    qtbot.mouseClick(window.env_box.btn_add_sta, Qt.MouseButton.LeftButton)
    obs_item = window.env_box.list_obs.item(0)
    obs_widget = window.env_box.list_obs.itemWidget(obs_item)
    qtbot.keyClicks(obs_widget.cb_sta, "c")

    routine = window._compose_routine()
    assert routine.vocs.observables == ["c"]


def test_add_random_points(qtbot):
    # test to add random points to initial points table
    from badger.gui.default.components.routine_page import BadgerRoutinePage

    window = BadgerRoutinePage()
    qtbot.addWidget(window)

    qtbot.keyClicks(window.env_box.cb, "test")
    qtbot.keyClicks(window.generator_box.cb, "random")

    window.env_box.var_table.cellWidget(0, 0).setChecked(True)
    window.env_box.var_table.cellWidget(1, 0).setChecked(True)
    window.env_box.var_table.cellWidget(2, 0).setChecked(True)

    def handle_dialog():
        while window.rc_dialog is None:
            QApplication.processEvents()

        # Set number of points to 5, frac to 0.05, then add them
        window.rc_dialog.sb_np.setValue(5)
        window.rc_dialog.sb_frac.setValue(0.05)
        qtbot.mouseClick(window.rc_dialog.btn_add, Qt.MouseButton.LeftButton)
    QTimer.singleShot(0, handle_dialog)

    qtbot.mouseClick(window.env_box.btn_add_rand, Qt.LeftButton)
    routine = window._compose_routine()

    assert routine.initial_points.shape[0] == 5
    # curr is 0, frac is 0.05, range is [-1, 1]
    # so max value should be 0.1, min value should be -0.1
    assert routine.initial_points.to_numpy().max() <= 0.1
    assert routine.initial_points.to_numpy().min() >= -0.1


# TODO: Test if the EI, Simplex, and RCDS params show o the params editor
# are the simplified versions
def test_simplified_generator_params(qtbot):
    pass


# TODO: First load an old routine w/ initail points,
# then create a new routine and check if the initial points panel
# is cleared
def test_initial_points_clear_when_create_routine(qtbot):
    pass


# TODO: Test if env selector reacts to scroll events, it should not
def test_scroll_on_environment_selector(qtbot):
    pass


# TODO: Test if generator selector reacts to scroll events, it should not
def test_scroll_on_generator_selector(qtbot):
    pass
