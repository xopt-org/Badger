import logging

from badger.utils import yprint

logger = logging.getLogger(__name__)


def show_intf(args):
    try:
        from badger.factory import list_intf, get_intf
    except Exception as e:
        logger.error(e)
        return

    if args.intf_name is None:
        yprint(list_intf())
        return

    try:
        _, configs = get_intf(args.intf_name)
        yprint(configs)
    except Exception as e:
        logger.error(e)
        try:
            # The exception could carry the configs information
            configs = e.configs
            yprint(configs)
        except:
            pass
