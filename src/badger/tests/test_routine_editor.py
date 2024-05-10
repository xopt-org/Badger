def test_init(qtbot):
    from badger.gui.default.components.routine_editor import BadgerRoutineEditor

    BadgerRoutineEditor()


def test_routine_set_and_save(qtbot):
    from badger.gui.default.components.routine_editor import BadgerRoutineEditor
    from badger.tests.utils import create_routine, fix_db_path_issue

    fix_db_path_issue()

    window = BadgerRoutineEditor()

    routine = create_routine()
    window.set_routine(routine)

    window.save_routine()
