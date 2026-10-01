"""The `badger install` command (currently disabled). Was intended for
installing plugins from a registry or local tarball — see docs for
the current plugin installation workflow."""

import logging
from argparse import Namespace

from typing_extensions import deprecated

logger = logging.getLogger(__name__)


@deprecated("The `badger install` command is currently disabled.")
def plugin_install(args: Namespace) -> None:
    print(
        "This command is currently disabled.\n"
        "Please refer to the Badger documentation for plugin management.\n\n"
        "Badger online documentation: https://xopt-org.github.io/Badger/"
    )
