import os
from importlib import metadata
from badger.actions.doctor import check_n_config_paths
from badger.utils import yprint
from badger.settings import init_settings, get_user_config_folder


def show_info(args):
    config_path = None

    if args.config_filepath:
        config_path = args.config_filepath

    if args.gui or args.gui_acr:
        if check_n_config_paths(args.config_filepath):
            from badger.gui import launch_gui

            launch_gui(config_path)

            return

    if not check_n_config_paths():
        return

    config_path = get_user_config_folder()
    configfile_path = os.path.join(config_path, "config.yaml")

    config_singleton = init_settings()
    BADGER_PLUGIN_ROOT = config_singleton.read_value("BADGER_PLUGIN_ROOT")
    BADGER_TEMPLATE_ROOT = config_singleton.read_value("BADGER_TEMPLATE_ROOT")
    BADGER_LOGBOOK_ROOT = config_singleton.read_value("BADGER_LOGBOOK_ROOT")
    BADGER_ARCHIVE_ROOT = config_singleton.read_value("BADGER_ARCHIVE_ROOT")
    BADGER_LOG_DIRECTORY = config_singleton.read_value("BADGER_LOG_DIRECTORY")
    BADGER_LOG_LEVEL = config_singleton.read_value("BADGER_LOG_LEVEL")
    BADGER_TENSOR_STRATEGY = config_singleton.read_value(
        "BADGER_PYTORCH_TENSOR_SHARING_STRATEGY"
    )
    info = {
        "name": "Badger the optimizer",
        "version": metadata.version("badger-opt"),
        "xopt version": metadata.version("xopt"),
        "config-file path": configfile_path,
        "plugin root": BADGER_PLUGIN_ROOT,
        "template root": BADGER_TEMPLATE_ROOT,
        "logbook root": BADGER_LOGBOOK_ROOT,
        "archive root": BADGER_ARCHIVE_ROOT,
        "logging directory": BADGER_LOG_DIRECTORY,
        "logging level": BADGER_LOG_LEVEL,
        "pytorch tensor sharing strategy": BADGER_TENSOR_STRATEGY,
        # 'plugin installation url': read_value('BADGER_PLUGINS_URL')
    }

    # print()  # put one blank line before the printout
    yprint(info)
