import logging

from badger.utils import yprint

logger = logging.getLogger(__name__)


def show_generator(args):
    try:
        from badger.factory import list_generators, get_generator
    except Exception as e:
        logger.error(e)
        return

    if args.generator_name is None:
        yprint(list_generators())
        return

    try:
        _, configs = get_generator(args.generator_name)
        yprint(configs)
    except Exception as e:
        logger.error(e)
        try:
            # The exception could carry the configs information
            configs = e.configs
            yprint(configs)
        except:
            pass
