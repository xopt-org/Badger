import pytest
import multiprocessing

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
    from badger.errors import BadgerRoutineError
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

    qtbot.keyClicks(window.generator_box.cb, "extremum_seeking")

    window.save()

    ids = list_routine()[0]
    assert len(ids) == 1
    for id in ids: remove_routine(id)

'''
class TestRoutineRunner:
    @pytest.fixture(scope="session")
    def init_multiprocessing(self):
        multiprocessing.set_start_method("fork", force=True)

    @pytest.fixture(scope="session")
    def init_multiprocessing_alt(self):
        # Use 'spawn' to start new processes instead of 'fork'
        multiprocessing.set_start_method("spawn", force=True)

    @pytest.fixture
    def process_manager(self):
        from badger.gui.default.components.create_process import CreateProcess
        from badger.gui.default.components.process_manager import ProcessManager

        process_manager = ProcessManager()
        process_builder = CreateProcess()
        process_builder.subprocess_prepared.connect(process_manager.add_to_queue)
        process_builder.create_subprocess()

        yield process_manager

        process_manager.close_proccesses()

    @pytest.fixture
    def instance(self, process_manager, routine):
        from badger.db import save_routine
        from badger.gui.default.components.routine_runner import (
            BadgerRoutineSubprocess,
        )
        from badger.tests.utils import create_routine, fix_db_path_issue

        fix_db_path_issue()

        instance = BadgerRoutineSubprocess(process_manager, routine)
        instance.pause_event = multiprocessing.Event()
        return instance

    # TODO: write test for modifying name of routine with runs
    def test_modify_routine_name(self, qtbot, instance):
        from badger.errors import BadgerRoutineError
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
        instance(routine)
        instance.run()


        ids = list_routine()[0]
        for id in ids: remove_routine(id)

    # TODO: write test for modifying algorithm of routine with runs
    def test_modify_routine_algorithm(self, qtbot):
        pass
'''
        