import os
import shutil
import pytest


@pytest.fixture(autouse=True)
def suppress_popups(mocker):
    mocker.patch(
        "badger.gui.default.windows.expandable_message_box.ExpandableMessageBox.exec_",
        return_value=None,
    )


@pytest.fixture(scope="module", autouse=True)
def config_test_settings(
    mock_plugin_root, mock_db_root, mock_logbook_root, mock_archive_root
):
    from badger.settings import init_settings

    config_singleton = init_settings()

    # Store the old values
    old_root = config_singleton.read_value("BADGER_PLUGIN_ROOT")
    old_db = config_singleton.read_value("BADGER_DB_ROOT")
    old_logbook = config_singleton.read_value("BADGER_LOGBOOK_ROOT")
    old_archived = config_singleton.read_value("BADGER_ARCHIVE_ROOT")

    # Assign values for test
    config_singleton.write_value("BADGER_PLUGIN_ROOT", mock_plugin_root)
    config_singleton.write_value("BADGER_DB_ROOT", mock_db_root)
    config_singleton.write_value("BADGER_LOGBOOK_ROOT", mock_logbook_root)
    config_singleton.write_value("BADGER_ARCHIVE_ROOT", mock_archive_root)

    yield

    # Restoring the original settings
    config_singleton.write_value("BADGER_PLUGIN_ROOT", old_root)
    config_singleton.write_value("BADGER_DB_ROOT", old_db)
    config_singleton.write_value("BADGER_LOGBOOK_ROOT", old_logbook)
    config_singleton.write_value("BADGER_ARCHIVE_ROOT", old_archived)


@pytest.fixture(scope="module", autouse=True)
def clean_up(mock_db_root, mock_logbook_root, mock_archive_root):
    # Clean before tests
    shutil.rmtree(mock_db_root, True)  # ignore errors
    shutil.rmtree(mock_logbook_root, True)
    shutil.rmtree(mock_archive_root, True)

    yield

    # Clean after tests
    shutil.rmtree(mock_db_root, True)
    shutil.rmtree(mock_logbook_root, True)
    shutil.rmtree(mock_archive_root, True)


@pytest.fixture(scope="module")
def mock_root(request):
    return os.path.join(request.fspath.dirname, "mock")


@pytest.fixture(scope="module")
def mock_plugin_root(mock_root):
    return os.path.join(mock_root, "plugins")


@pytest.fixture(scope="module")
def mock_db_root(mock_root):
    return os.path.join(mock_root, "db")


@pytest.fixture(scope="module")
def mock_logbook_root(mock_root):
    return os.path.join(mock_root, "logbook")


@pytest.fixture(scope="module")
def mock_archive_root(mock_root):
    return os.path.join(mock_root, "archived")


@pytest.fixture(scope="module")
def mock_config_root(mock_root):
    return os.path.join(mock_root, "configs")
