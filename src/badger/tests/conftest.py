import os
import shutil

import pytest
from PyQt5.QtWidgets import QDialog


@pytest.fixture(autouse=True)
def suppress_popups(mocker):
    mocker.patch(
        "badger.gui.windows.expandable_message_box.ExpandableMessageBox.exec_",
        return_value=None,
    )
    mocker.patch(
        "badger.gui.windows.termination_reached_dialog.BadgerTerminationReachedDialog.exec_",
        return_value=QDialog.Rejected,
    )


@pytest.fixture(scope="session", autouse=True)
def recover_config_from_crash():
    """Restore the user config if a previous test session was killed mid-run.

    The per-module fixture writes a ``.pytest-backup`` sidecar before mutating
    the real config. If the process dies before teardown (e.g. SIGKILL), that
    sidecar is left behind holding the original config; restore it here before
    any test touches the config so the user's real settings are never lost.
    """
    from badger.settings import init_settings

    config_singleton = init_settings()
    config_path = config_singleton.config_path
    backup_path = f"{config_path}.pytest-backup"
    if os.path.exists(backup_path):
        shutil.copyfile(backup_path, config_path)
        os.remove(backup_path)
        config_singleton.reload()
    yield


@pytest.fixture(scope="module", autouse=True)
def config_test_settings(
    mock_plugin_root,
    mock_template_root,
    mock_logbook_root,
    mock_archive_root,
    mock_log_directory,
    mock_logging_level,
    mock_temp_directory,
):
    from badger.settings import init_settings

    config_singleton = init_settings()
    config_path = config_singleton.config_path
    backup_path = f"{config_path}.pytest-backup"

    # Snapshot the original values so each can be restored independently.
    # A missing key (older config) is simply skipped instead of aborting the
    # whole restore, which previously left the config in the mock test state.
    keys = [
        "BADGER_PLUGIN_ROOT",
        "BADGER_TEMPLATE_ROOT",
        "BADGER_LOGBOOK_ROOT",
        "BADGER_ARCHIVE_ROOT",
        "BADGER_LOG_DIRECTORY",
        "BADGER_LOG_LEVEL",
        "BADGER_TEMP_DIRECTORY",
    ]
    original_values = {}
    for key in keys:
        try:
            original_values[key] = config_singleton.read_value(key)
        except KeyError:
            pass

    mock_values = {
        "BADGER_PLUGIN_ROOT": mock_plugin_root,
        "BADGER_TEMPLATE_ROOT": mock_template_root,
        "BADGER_LOGBOOK_ROOT": mock_logbook_root,
        "BADGER_ARCHIVE_ROOT": mock_archive_root,
        "BADGER_LOG_DIRECTORY": mock_log_directory,
        "BADGER_LOG_LEVEL": mock_logging_level,
        "BADGER_TEMP_DIRECTORY": mock_temp_directory,
    }

    # Crash safety net: keep a verbatim copy of the real config on disk so a
    # hard kill before teardown can be recovered on the next session start.
    shutil.copyfile(config_path, backup_path)

    try:
        for key, value in mock_values.items():
            config_singleton.write_value(key, value)
        yield
    finally:
        # Always restore the original settings, even if a test raised.
        for key, value in original_values.items():
            config_singleton.write_value(key, value)
        if os.path.exists(backup_path):
            os.remove(backup_path)


@pytest.fixture(scope="module", autouse=True)
def clean_up(
    mock_template_root,
    mock_logbook_root,
    mock_archive_root,
    mock_log_directory,
    mock_temp_directory,
):
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
def mock_root(request):
    return os.path.join(request.fspath.dirname, "mock")


@pytest.fixture(scope="module")
def mock_plugin_root(mock_root):
    return os.path.join(mock_root, "plugins")


@pytest.fixture(scope="module")
def mock_template_root(mock_root):
    return os.path.join(mock_root, "templates")


@pytest.fixture(scope="module")
def mock_logbook_root(mock_root):
    return os.path.join(mock_root, "logbook")


@pytest.fixture(scope="module")
def mock_archive_root(mock_root):
    return os.path.join(mock_root, "archived")


@pytest.fixture(scope="module")
def mock_log_directory(mock_root):
    return os.path.join(mock_root, "logs")


@pytest.fixture(scope="module")
def mock_temp_directory(mock_root):
    return os.path.join(mock_root, "temp")


@pytest.fixture(scope="module")
def mock_logging_level(mock_root):
    return "WARNING"


@pytest.fixture(scope="module")
def mock_config_root(mock_root):
    return os.path.join(mock_root, "configs")
