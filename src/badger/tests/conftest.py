import os
import shutil
import tempfile

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
    real_config_path = config_singleton.config_path

    mock_values = {
        "BADGER_PLUGIN_ROOT": mock_plugin_root,
        "BADGER_TEMPLATE_ROOT": mock_template_root,
        "BADGER_LOGBOOK_ROOT": mock_logbook_root,
        "BADGER_ARCHIVE_ROOT": mock_archive_root,
        "BADGER_LOG_DIRECTORY": mock_log_directory,
        "BADGER_LOG_LEVEL": mock_logging_level,
        "BADGER_TEMP_DIRECTORY": mock_temp_directory,
    }

    # Run the tests against a throwaway copy of the user's config and point the
    # singleton at it. The real config file on disk is never written to, so a
    # hard kill mid-run can never leave the user's active config pointing at
    # test paths.
    fd, temp_config_path = tempfile.mkstemp(suffix=".yaml")
    os.close(fd)
    try:
        shutil.copyfile(real_config_path, temp_config_path)
        config_singleton.config_path = temp_config_path
        config_singleton.reload()

        for key, value in mock_values.items():
            config_singleton.write_value(key, value)
        yield
    finally:
        # Point the singleton back at the untouched real config.
        config_singleton.config_path = real_config_path
        config_singleton.reload()
        if os.path.exists(temp_config_path):
            os.remove(temp_config_path)


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
