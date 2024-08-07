import pytest
from badger.db import load_routine, remove_routine
from PyQt5.QtCore import pyqtSignal

def test_routine_add_variable(qtbot):
    from badger.errors import BadgerRoutineError

    # test if a simple routine can be created
    from badger.gui.default.components.routine_page import BadgerRoutinePage

    window = BadgerRoutinePage()
    qtbot.addWidget(window)

    # add generator -- still should raise error for no environment
    qtbot.keyClicks(window.generator_box.cb, "expected_improvement")
    with pytest.raises(BadgerRoutineError):
        window._compose_routine()

    # finally add the test environment
    qtbot.keyClicks(window.env_box.cb, "sphere_epics")

    # click checkbox to select vars/objectives
    window.env_box.var_table.cellWidget(0, 0).setChecked(True)
    assert window.env_box.var_table.export_variables() == {"SPHERE:X1": [-1, 1]}

    # Check that there is an extra row: X1, X2, and one to enter a new PV
    n_rows = window.env_box.var_table.rowCount()
    assert n_rows == 3

    # Enter text in first cell of last row
    item = window.env_box.var_table.item(2, 1)
    item.setText("SPHERE:X3")
    assert window.env_box.var_table.item(2, 1).text() == "SPHERE:X3"

    # Send signal of table item changing
    window.env_box.var_table.cellChanged.emit(2, 1)

    # Why isn't this updating the table after changing the value?
    variables = {
        "SPHERE:X1": [-1, 1],
        "SPHERE:X3": [-1, 1]
    }

    # Make sure it's checked (what should default be?)
    window.env_box.var_table.cellWidget(2, 0).setChecked(True)

    # Check that new variable was added
    assert window.env_box.var_table.export_variables() == variables

    # Check that a new row was automatically added
    assert window.env_box.var_table.rowCount() == n_rows + 1

    # Check VOCS
    routine = window._compose_routine()
    assert routine.vocs.variables == variables

    # Check saved routine
    window.save()
    new_routine, _ = load_routine(routine.name)
    assert new_routine.vocs == routine.vocs
    # TODO: Add addtl_vars to routine page?
    # TODO: reloading does not work becuase additional_variables is not in VOCS
    # TODO: this is not retrieving the YAML
    # assert routine.vocs.additional_variables == window.env_box.var_table.addtl_vars

    remove_routine(routine.name)
