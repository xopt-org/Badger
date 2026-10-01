import os
import shutil
from collections.abc import Generator

import pytest
from _pytest.fixtures import FixtureRequest
from PyQt5.QtWidgets import QDialog
from pytest_mock import MockerFixture

# Stash key holding the user's real plugin root so it can be restored at session end.
_OLD_PLUGIN_ROOT: pytest.StashKey[str | None] = pytest.StashKey()


def pytest_configure(config: pytest.Config) -> None:
    # badger.factory captures BADGER_PLUGIN_ROOT at import time, which happens during
    # collection. Point it at the mock plugins now, before any test module is imported.
    from badger.settings import init_settings

    settings = init_settings()
    try:
        config.stash[_OLD_PLUGIN_ROOT] = settings.read_value("BADGER_PLUGIN_ROOT")
    except KeyError:
        config.stash[_OLD_PLUGIN_ROOT] = None

    mock_plugin_root = os.path.join(os.path.dirname(__file__), "mock", "plugins")
    settings.write_value("BADGER_PLUGIN_ROOT", mock_plugin_root)


def pytest_unconfigure(config: pytest.Config) -> None:
    old_plugin_root = config.stash.get(_OLD_PLUGIN_ROOT, None)
    if old_plugin_root is not None:
        from badger.settings import init_settings

        init_settings().write_value("BADGER_PLUGIN_ROOT", old_plugin_root)


@pytest.fixture(autouse=True)
def _ensure_qapp(qapp: object) -> None:
    # Guarantee pytest-qt's QApplication exists before any widget is constructed,
    # so tests that build Qt widgets without requesting qtbot don't abort when run
    # in isolation (e.g. VS Code's Testing panel).
    return None


@pytest.fixture(autouse=True)
def _reap_subprocesses() -> Generator[None, None, None]:
    # Safety net: terminate any optimization subprocess a test leaves running.
    # A leaked child inherits the pytest stdout pipe and keeps it open, so the
    # test runner never sees EOF and hangs "indefinitely" (e.g. VS Code Testing).
    import multiprocessing

    yield

    children = multiprocessing.active_children()
    for child in children:
        child.terminate()
    for child in children:
        child.join(timeout=2)
        if child.is_alive():
            child.kill()
            child.join(timeout=1)


@pytest.fixture(autouse=True)
def suppress_popups(mocker: MockerFixture) -> None:
    mocker.patch(
        "badger.gui.windows.expandable_message_box.ExpandableMessageBox.exec_",
        return_value=None,
    )
    mocker.patch(
        "badger.gui.windows.termination_reached_dialog.BadgerTerminationReachedDialog.exec_",
        return_value=QDialog.Rejected,
    )


@pytest.fixture(scope="module", autouse=True)
def config_test_settings(
    mock_template_root: str,
    mock_logbook_root: str,
    mock_archive_root: str,
    mock_log_directory: str,
    mock_logging_level: str,
    mock_temp_directory: str,
) -> Generator[None, None, None]:

    from badger.settings import init_settings

    config_singleton = init_settings()

    # Store the old values
    # If user's config is missing any values (for example if have older config missing newer added config options),
    # 'read_value' throws a KeyError which we can ignore
    # BADGER_PLUGIN_ROOT is handled in pytest_configure (it must be set before collection).
    try:
        old_template = config_singleton.read_value("BADGER_TEMPLATE_ROOT")
        old_logbook = config_singleton.read_value("BADGER_LOGBOOK_ROOT")
        old_archived = config_singleton.read_value("BADGER_ARCHIVE_ROOT")
        old_log_directory = config_singleton.read_value("BADGER_LOG_DIRECTORY")
        old_logging_level = config_singleton.read_value("BADGER_LOG_LEVEL")
        old_temp_directory = config_singleton.read_value("BADGER_TEMP_DIRECTORY")
    except KeyError:
        pass

    # Assign values for test
    config_singleton.write_value("BADGER_TEMPLATE_ROOT", mock_template_root)
    config_singleton.write_value("BADGER_LOGBOOK_ROOT", mock_logbook_root)
    config_singleton.write_value("BADGER_ARCHIVE_ROOT", mock_archive_root)
    config_singleton.write_value("BADGER_LOG_DIRECTORY", mock_log_directory)
    config_singleton.write_value("BADGER_LOG_LEVEL", mock_logging_level)
    config_singleton.write_value("BADGER_TEMP_DIRECTORY", mock_temp_directory)
    yield

    # Restoring the original settings
    try:
        config_singleton.write_value("BADGER_TEMPLATE_ROOT", old_template)
        config_singleton.write_value("BADGER_LOGBOOK_ROOT", old_logbook)
        config_singleton.write_value("BADGER_ARCHIVE_ROOT", old_archived)
        config_singleton.write_value("BADGER_LOG_DIRECTORY", old_log_directory)
        config_singleton.write_value("BADGER_LOG_LEVEL", old_logging_level)
        config_singleton.write_value("BADGER_TEMP_DIRECTORY", old_temp_directory)
    # check if any "old_..." vars didn't get created b/c any of the config values didn't exist in user's config.
    except NameError:
        pass


@pytest.fixture(scope="module", autouse=True)
def clean_up(
    mock_template_root: str,
    mock_logbook_root: str,
    mock_archive_root: str,
    mock_log_directory: str,
    mock_temp_directory: str,
) -> Generator[None, None, None]:
    # Clean before tests
    shutil.rmtree(mock_template_root, True)  # ignore errors
    shutil.rmtree(mock_logbook_root, True)
    shutil.rmtree(mock_archive_root, True)
    shutil.rmtree(mock_log_directory, True)
    shutil.rmtree(mock_temp_directory, True)

    yield

    # Clean after tests
    shutil.rmtree(mock_template_root, True)
    shutil.rmtree(mock_logbook_root, True)
    shutil.rmtree(mock_archive_root, True)
    shutil.rmtree(mock_log_directory, True)
    shutil.rmtree(mock_temp_directory, True)


@pytest.fixture(scope="module")
def mock_root(request: FixtureRequest) -> str:
    return os.path.join(request.path.parent, "mock")


@pytest.fixture(scope="module")
def mock_plugin_root(mock_root: str) -> str:
    return os.path.join(mock_root, "plugins")


@pytest.fixture(scope="module")
def mock_template_root(mock_root: str) -> str:
    return os.path.join(mock_root, "templates")


@pytest.fixture(scope="module")
def mock_logbook_root(mock_root: str) -> str:
    return os.path.join(mock_root, "logbook")


@pytest.fixture(scope="module")
def mock_archive_root(mock_root: str) -> str:
    return os.path.join(mock_root, "archived")


@pytest.fixture(scope="module")
def mock_log_directory(mock_root: str) -> str:
    return os.path.join(mock_root, "logs")


@pytest.fixture(scope="module")
def mock_temp_directory(mock_root: str) -> str:
    return os.path.join(mock_root, "temp")


@pytest.fixture(scope="module")
def mock_logging_level(mock_root: str) -> str:
    return "WARNING"


@pytest.fixture(scope="module")
def mock_config_root(mock_root: str) -> str:
    return os.path.join(mock_root, "configs")
