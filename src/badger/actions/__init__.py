from pkg_resources import get_distribution
from .doctor import check_n_config_paths
from ..utils import yprint
from ..log import set_log_level


def show_info(args):
    # Change log level for all existed loggers
    set_log_level(args.log)

    if args.gui:
        if check_n_config_paths():
            from ..gui.default import launch_gui

            launch_gui()

        return

    if args.gui_acr:
        if check_n_config_paths():
            from ..gui.default import launch_gui

            launch_gui()

        return

    if not check_n_config_paths():
        return

    from ..settings import read_value

    BADGER_PLUGIN_ROOT = read_value("BADGER_PLUGIN_ROOT")
    BADGER_DB_ROOT = read_value("BADGER_DB_ROOT")
    BADGER_LOGBOOK_ROOT = read_value("BADGER_LOGBOOK_ROOT")
    BADGER_ARCHIVE_ROOT = read_value("BADGER_ARCHIVE_ROOT")

    info = {
        'name': 'Badger the optimizer',
        'version': get_distribution('badger-opt').version,
        'plugin root': BADGER_PLUGIN_ROOT,
        'database root': BADGER_DB_ROOT,
        'logbook root': BADGER_LOGBOOK_ROOT,
        'archive root': BADGER_ARCHIVE_ROOT,
        # 'plugin installation url': read_value('BADGER_PLUGINS_URL')
    }

    # print()  # put one blank line before the printout
    yprint(info)
