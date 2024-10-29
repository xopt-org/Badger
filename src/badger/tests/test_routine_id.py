def test_routines_same_name():
    from badger.db import save_routine, remove_routine
    from badger.tests.utils import create_routine, fix_db_path_issue

    fix_db_path_issue()

    routine1 = create_routine()
    routine2 = create_routine()
    save_routine(routine1)
    save_routine(routine2)

    assert routine1.id != routine2.id

    remove_routine(routine1.id)
    remove_routine(routine2.id)


def test_modify_routine_no_runs(qtbot):
    from badger.gui.default.components.routine_page import BadgerRoutinePage
    from badger.db import list_routine, remove_routine, load_routine

    window = BadgerRoutinePage()
    qtbot.addWidget(window)
    window.env_box.relative_to_curr.setChecked(False)
    qtbot.keyClicks(window.generator_box.cb, "expected_improvement")
    qtbot.keyClicks(window.env_box.cb, "test")

    window.env_box.var_table.cellWidget(0, 0).setChecked(True)
    assert window.env_box.var_table.export_variables() == {"x0": [-1, 1]}

    window.env_box.obj_table.cellWidget(0, 0).setChecked(True)
    assert window.env_box.obj_table.export_objectives() == {"f": "MINIMIZE"}

    window.save()
    id = list_routine()[0][0]
    routine, _ = load_routine(id)
    window.refresh_ui(routine)

    index = window.generator_box.cb.findText("extremum_seeking")
    window.generator_box.cb.setCurrentIndex(index)
    window.save()

    ids = list_routine()[0]
    assert len(ids) == 1
    for id in ids:
        remove_routine(id)


# TODO: write test for modifying name of routine with runs
def test_modify_routine_name(qtbot):
    from badger.gui.default.components.routine_page import BadgerRoutinePage
    from badger.db import list_routine, remove_routine, load_routine, save_run

    window = BadgerRoutinePage()
    qtbot.addWidget(window)
    window.env_box.relative_to_curr.setChecked(False)
    qtbot.keyClicks(window.generator_box.cb, "expected_improvement")
    qtbot.keyClicks(window.env_box.cb, "test")
    window.env_box.var_table.cellWidget(0, 0).setChecked(True)
    window.env_box.obj_table.cellWidget(0, 0).setChecked(True)

    window.save()
    id = list_routine()[0][0]
    routine, _ = load_routine(id)
    window.refresh_ui(routine)

    run = {
        "filename": "BadgerOpt-2024-09-10-155408.yaml",
        "routine": routine,
        "data": {
            "f": [0.051416649999999994],
            "timestamp": [1729263544.34316],
            # 'x0': [-0.1711],
            # 'xopt_error': [False],
            # 'xopt_runtime': [0.0007418617606163025]
        },
    }
    save_run(run)

    window.edit_save.setText("new_name")
    window.save()

    ids = list_routine()[0]
    assert len(ids) == 1
    for id in ids:
        remove_routine(id)


# TODO: write test for modifying algorithm of routine with runs
def test_modify_routine_algorithm(qtbot):
    from badger.gui.default.components.routine_page import BadgerRoutinePage
    from badger.db import list_routine, remove_routine, load_routine, save_run

    window = BadgerRoutinePage()
    qtbot.addWidget(window)
    window.env_box.relative_to_curr.setChecked(False)
    qtbot.keyClicks(window.generator_box.cb, "expected_improvement")
    qtbot.keyClicks(window.env_box.cb, "test")
    window.env_box.var_table.cellWidget(0, 0).setChecked(True)
    window.env_box.obj_table.cellWidget(0, 0).setChecked(True)

    window.save()
    id = list_routine()[0][0]
    routine, _ = load_routine(id)
    window.refresh_ui(routine)

    run = {
        "filename": "BadgerOpt-2024-09-10-155408.yaml",
        "routine": routine,
        "data": {
            "f": [0.051416649999999994],
            "timestamp": [1729263544.34316],
            # 'x0': [-0.1711],
            # 'xopt_error': [False],
            # 'xopt_runtime': [0.0007418617606163025]
        },
    }
    save_run(run)

    index = window.generator_box.cb.findText("extremum_seeking")
    window.generator_box.cb.setCurrentIndex(index)
    window.save()

    ids = list_routine()[0]
    assert len(ids) == 2
    for id in ids:
        remove_routine(id)
