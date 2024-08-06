import pytest

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
    qtbot.keyClicks(window.env_box.cb, "test")

    # click checkbox to select vars/objectives
    window.env_box.var_table.cellWidget(0, 0).setChecked(True)
    assert window.env_box.var_table.export_variables() == {"x0": [-1, 1]}

    ####################
    ### TO IMPLEMENT ###

    # Check that there is an extra row
    vars = window.env_box.var_table.export_variables().keys()
    n_vars = len(vars)
    n_rows = window.env_box.var_table.rowCount()
    assert n_rows == n_vars + 1

    # TODO: how to read in text
    # TODO: where to assign input to add var
    # TODO: data flow from there to export_variables?

    # Enter text in first cell of last row
    window.env_box.var_table.cellWidget(n_rows, 0). ADD/READ IN TEXT # "x1": [-1, 1]

    # Make sure it's checked (what should default be?)
    # window.env_box.var_table.cellWidget(n_rows, 0).setChecked(True)

    # Check that new variable was added
    assert window.env_box.var_table.export_variables() == {"x0": [-1, 1], "x20": [-1, 1]}

    # Check that a new row was automatically added
    assert window.env_box.var_table.rowCount() == n_rows + 1

    routine = window._compose_routine()
    assert routine.vocs.variables == {"x0": [-1, 1], "x20": [-1, 1]}
    # TODO: add under new "additional variables" key in VOCS
    assert routine.vocs.additional_variables == {"x20": [-1, 1]}

    ####################
    ####################