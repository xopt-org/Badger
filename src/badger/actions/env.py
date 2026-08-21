"""The `badger env` command. Lists available environment plugins or shows
the details (variables, observations, parameters) of a specific one."""

import argparse
import logging

from badger.errors import BadgerInvalidPluginError, BadgerPluginNotFoundError
from badger.utils import range_to_str, yprint

logger = logging.getLogger(__name__)


def show_env(args: argparse.Namespace) -> None:
    try:
        from badger.factory import get_env, list_env
    except Exception:
        logger.exception("Failed to import environment plugins.")
        return

    if args.env_name is None:
        yprint(list_env())
        return

    try:
        _, configs = get_env(args.env_name)
    except BadgerPluginNotFoundError as e:
        logger.error(e)
        return
    except BadgerInvalidPluginError as e:
        logger.error(e)
        # The exception carries the configs information
        if e.configs is None:
            return
        configs = e.configs

    try:
        configs["variables"] = range_to_str(configs["variables"])
        yprint(configs)
    except (KeyError, TypeError):
        logger.exception(
            "Failed to show environment details. The configs may be malformed."
        )
