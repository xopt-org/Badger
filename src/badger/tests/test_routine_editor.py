def test_init(qtbot):
    from badger.gui.acr.components.routine_editor import BadgerRoutineEditor

    BadgerRoutineEditor()


def test_routine_set_and_save(qtbot):
    from badger.gui.acr.components.routine_editor import BadgerRoutineEditor
    from badger.tests.utils import create_routine

    window = BadgerRoutineEditor()

    routine = create_routine()
    window.set_routine(routine)

    # TODO: Test save tmp routine stuff
    # window.save_routine()
