"""The `badger interface` command. Lists available interface plugins or
shows the details of a specific one."""

import logging

from badger.errors import BadgerInvalidPluginError, BadgerPluginNotFoundError
from badger.utils import yprint

logger = logging.getLogger(__name__)


def show_intf(args):
    try:
        from badger.factory import get_intf, list_intf
    except Exception as e:  # noqa: BLE001 - import triggers config/plugin loading; report and exit
        logger.error(e)
        return

    if args.intf_name is None:
        yprint(list_intf())
        return

    try:
        _, configs = get_intf(args.intf_name)
        yprint(configs)
    except BadgerPluginNotFoundError as e:
        logger.error(e)
        return
    except BadgerInvalidPluginError as e:
        logger.error(e)
        # The exception carries the configs information
        if e.configs is None:
            logger.warning("Failed to retrieve interface configs from exception")
            return
        yprint(e.configs)
