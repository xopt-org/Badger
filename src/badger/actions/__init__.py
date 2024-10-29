from importlib import metadata
from badger.actions.doctor import check_n_config_paths
from badger.utils import yprint
from badger.log import set_log_level


def show_info(args):
    # Change log level for all existed loggers
    set_log_level(args.log)

    if args.gui:
        if check_n_config_paths():
            from badger.gui.default import launch_gui

            launch_gui()

        return

    if args.gui_acr:
        if check_n_config_paths():
            from badger.gui.default import launch_gui

            launch_gui()

        return

    if not check_n_config_paths():
        return

    from badger.settings import init_settings

    config_singleton = init_settings()
    BADGER_PLUGIN_ROOT = config_singleton.read_value("BADGER_PLUGIN_ROOT")
    BADGER_DB_ROOT = config_singleton.read_value("BADGER_DB_ROOT")
    BADGER_LOGBOOK_ROOT = config_singleton.read_value("BADGER_LOGBOOK_ROOT")
    BADGER_ARCHIVE_ROOT = config_singleton.read_value("BADGER_ARCHIVE_ROOT")

    info = {
        "name": "Badger the optimizer",
        "version": metadata.version("badger-opt"),
        "plugin root": BADGER_PLUGIN_ROOT,
        "database root": BADGER_DB_ROOT,
        "logbook root": BADGER_LOGBOOK_ROOT,
        "archive root": BADGER_ARCHIVE_ROOT,
        # 'plugin installation url': read_value('BADGER_PLUGINS_URL')
    }

    # print()  # put one blank line before the printout
    yprint(info)
