"""The `badger env` command. Lists available environment plugins or shows
the details (variables, observations, parameters) of a specific one."""

import argparse
import logging

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
        logger.exception(
            "Failed to show environment details. The configs may be malformed."
        )
