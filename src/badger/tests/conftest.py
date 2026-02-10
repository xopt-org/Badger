import os
import shutil
import pytest


@pytest.fixture(autouse=True)
def suppress_popups(mocker):
    mocker.patch(
        "badger.gui.windows.expandable_message_box.ExpandableMessageBox.exec_",
        return_value=None,
    )


@pytest.fixture(scope="module", autouse=True)
def config_test_settings(
    mock_plugin_root,
    mock_template_root,
    mock_logbook_root,
    mock_archive_root,
    mock_log_directory,
    mock_logging_level,
):
    from badger.settings import init_settings

    config_singleton = init_settings()

    # Store the old values
    # If user's config is missing any values (for example if have older config missing newer added config options),
    # 'read_value' throws a KeyError which we can ignore
    try:
        old_root = config_singleton.read_value("BADGER_PLUGIN_ROOT")
        old_template = config_singleton.read_value("BADGER_TEMPLATE_ROOT")
        old_logbook = config_singleton.read_value("BADGER_LOGBOOK_ROOT")
        old_archived = config_singleton.read_value("BADGER_ARCHIVE_ROOT")
        old_log_directory = config_singleton.read_value("BADGER_LOG_DIRECTORY")
        old_logging_level = config_singleton.read_value("BADGER_LOG_LEVEL")
    except KeyError:
        pass

    # Assign values for test
    config_singleton.write_value("BADGER_PLUGIN_ROOT", mock_plugin_root)
    config_singleton.write_value("BADGER_TEMPLATE_ROOT", mock_template_root)
    config_singleton.write_value("BADGER_LOGBOOK_ROOT", mock_logbook_root)
    config_singleton.write_value("BADGER_ARCHIVE_ROOT", mock_archive_root)
    config_singleton.write_value("BADGER_LOG_DIRECTORY", mock_log_directory)
    config_singleton.write_value("BADGER_LOG_LEVEL", mock_logging_level)

    yield

    # Restoring the original settings
    try:
        config_singleton.write_value("BADGER_PLUGIN_ROOT", old_root)
        config_singleton.write_value("BADGER_TEMPLATE_ROOT", old_template)
        config_singleton.write_value("BADGER_LOGBOOK_ROOT", old_logbook)
        config_singleton.write_value("BADGER_ARCHIVE_ROOT", old_archived)
        config_singleton.write_value("BADGER_LOG_DIRECTORY", old_log_directory)
        config_singleton.write_value("BADGER_LOG_LEVEL", old_logging_level)
    # check if any "old_..." vars didn't get created b/c any of the config values didn't exist in user's config.
    except NameError:
        pass


@pytest.fixture(scope="module", autouse=True)
def clean_up(
    mock_template_root, mock_logbook_root, mock_archive_root, mock_log_directory
):
    # Clean before tests
    shutil.rmtree(mock_template_root, True)  # ignore errors
    shutil.rmtree(mock_logbook_root, True)
    shutil.rmtree(mock_archive_root, True)
    shutil.rmtree(mock_log_directory, True)

    yield

    # Clean after tests
    shutil.rmtree(mock_template_root, True)
    shutil.rmtree(mock_logbook_root, True)
    shutil.rmtree(mock_archive_root, True)
    shutil.rmtree(mock_log_directory, True)


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
def mock_logging_level(mock_root):
    return "WARNING"


@pytest.fixture(scope="module")
def mock_config_root(mock_root):
    return os.path.join(mock_root, "configs")
