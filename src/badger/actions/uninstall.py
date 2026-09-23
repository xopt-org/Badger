"""The `badger uninstall` command (currently disabled). Was intended for
removing plugins — see docs for the current workflow."""

import logging

from typing_extensions import deprecated

logger = logging.getLogger(__name__)


@deprecated("The `badger uninstall` command is currently disabled.")
def plugin_remove(args):
    print(
        "This command is currently disabled.\n"
        "Please refer to the Badger documentation for plugin management.\n\n"
        "Badger online documentation: https://xopt-org.github.io/Badger/"
    )
