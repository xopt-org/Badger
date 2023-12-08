def test_data_viewer_simple(qtbot):
    from badger.gui.default.components.analysis_extensions import AnalysisExtension
    from badger.tests.utils import create_routine

    routine = create_routine()
    routine.evaluate_data(routine.initial_points)

    data_viewer = AnalysisExtension()
    data_viewer.update_window(routine)
