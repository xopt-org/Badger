import logging

from badger.utils import range_to_str, yprint

logger = logging.getLogger(__name__)


def show_env(args):
    try:
        from badger.factory import list_env, get_env
    except Exception as e:
        logger.error(e)
        return

    if args.env_name is None:
        yprint(list_env())
        return

    try:
        _, configs = get_env(args.env_name)
    except Exception as e:
        logger.error(e)
        try:
            # The exception could carry the configs information
            configs = e.configs
        except:
            return

    try:
        configs["variables"] = range_to_str(configs["variables"])
        yprint(configs)
    except:
        pass
