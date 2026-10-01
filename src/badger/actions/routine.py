"""The `badger routine` command. Lists, inspects, or runs saved routines
from the terminal. Deprecated in favor of the GUI but kept for
backwards compatibility."""

import logging
from argparse import Namespace

from typing_extensions import deprecated

logger = logging.getLogger(__name__)


@deprecated("The `badger routine` command is deprecated. Please use the GUI.")
def show_routine(args: Namespace) -> None:
    print(
        "This command is deprecated.\n"
        "Please use 'badger -g' to launch the Badger GUI "
        "and manage routines/runs."
    )
