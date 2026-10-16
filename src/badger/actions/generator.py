"""The `badger generator` command. Lists available optimization algorithms
or shows the default configuration of a specific one."""

import logging

from xopt.errors import XoptError

from badger.utils import yprint

logger = logging.getLogger(__name__)


def show_generator(args):
    try:
        from badger.factory import get_generator, list_generators
    except Exception as e:  # noqa: BLE001 - import triggers config/plugin loading; report and exit
        logger.error(e)
        return

    if args.generator_name is None:
        yprint(list_generators())
        return

    try:
        configs = get_generator(args.generator_name)
        yprint(configs)
    except XoptError as e:
        logger.error(e)
