"""Tests for Badger CLI routine running (headless and GUI mode handlers)."""

from textwrap import dedent
from unittest.mock import MagicMock

import pytest

from badger.actions.run import run_routine_cli
from badger.routine import Routine, calculate_initial_points
from badger.utils import load_template_file


@pytest.fixture
def sample_template_file(tmp_path):
    # 'dedent' = remove common leading white space. so it's easier to read here
    template_content = dedent("""\
        name: test_cli_routine
        description: "CLI routine test"
        environment:
          name: test
        generator:
          name: random
        vocs:
          variables:
            x0: [0.0, 1.0]
            x1: [0.0, 1.0]
          objectives:
            y0: MINIMIZE
        initial_point_actions:
          - type: add_curr
    """)
    file_path = tmp_path / "routine_test.yaml"
    file_path.write_text(template_content)
    return str(file_path)


def test_routine_creation(sample_template_file):
    config = load_template_file(sample_template_file)

    routine = Routine(**config)
    assert routine.creation_ts is not None
    assert isinstance(routine.creation_ts, str)
    assert len(routine.creation_ts) > 0


def test_calculate_initial_points(sample_template_file):
    config = load_template_file(sample_template_file)
    routine = Routine(**config)

    # Test passing 'None' into initial_point_actions
    init_points = calculate_initial_points(None, routine.vocs, routine.environment)
    assert isinstance(init_points, dict)
    assert "x0" in init_points
    assert len(init_points["x0"]) == 0
    assert "x1" in init_points
    assert len(init_points["x1"]) == 0


def test_run_routine_cli_headless_auto_run(sample_template_file, mocker):
    mocker.patch("badger.actions.run.run_routine_headless")

    args = MagicMock()
    args.template_file = sample_template_file
    args.template_string = None
    args.headless = True
    args.auto_run = True

    from badger.actions.run import run_routine_headless as mock_headless

    run_routine_cli(args)

    mock_headless.assert_called_once()
    called_routine = mock_headless.call_args[0][0]
    assert called_routine.name == "test_cli_routine"
    assert mock_headless.call_args[1]["auto_run"] is True


def test_run_routine_cli_gui_mode(sample_template_file, mocker):
    mocker.patch("badger.actions.run.run_routine_gui")

    args = MagicMock()
    args.template_file = sample_template_file
    args.template_string = None
    args.headless = False
    args.auto_run = False

    from badger.actions.run import run_routine_gui as mock_gui

    run_routine_cli(args)

    mock_gui.assert_called_once()
    called_routine = mock_gui.call_args[0][0]
    assert called_routine.name == "test_cli_routine"
    assert mock_gui.call_args[1]["auto_run"] is False


def test_run_routine_cli_template_string(mocker):
    mocker.patch("badger.actions.run.run_routine_headless")

    template_str = dedent("""\
        name: string_test_routine
        environment:
          name: test
        generator:
          name: random
        vocs:
          variables:
            x0: [0.0, 1.0]
          objectives:
            y0: MINIMIZE
    """)

    args = MagicMock()
    args.template_file = None
    args.template_string = template_str
    args.headless = True
    args.auto_run = True

    from badger.actions.run import run_routine_headless as mock_headless

    run_routine_cli(args)

    mock_headless.assert_called_once()
    called_routine = mock_headless.call_args[0][0]
    # Check that template_str was read correctly
    assert called_routine.name == "string_test_routine"
