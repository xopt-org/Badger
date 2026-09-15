"""The `badger routine` command. Lists, inspects, or runs saved routines
from the terminal. Deprecated in favor of the GUI but kept for
backwards compatibility."""

import logging

logger = logging.getLogger(__name__)


def show_routine(args):
    print(
        "This command is deprecated.\n"
        "Please use 'badger -g' to launch the Badger GUI "
        "and manage routines/runs."
    )

    # try:
    #     from badger.actions.run import run_n_archive
    #     from badger.db import list_routine, load_routine
    # except Exception as e:
    #     logger.error(e)
    #     return

    # # List routines
    # if args.routine_id is None:
    #     routines = list_routine()[1]
    #     if routines:
    #         yprint(routines)
    #     else:
    #         print("No routine has been saved yet")
    #     return

    # try:
    #     routine, _ = load_routine(args.routine_id)
    #     if routine is None:
    #         print(f"Routine {args.routine_id} not found")
    #         return
    # except Exception as e:
    #     print(e)
    #     return

    # # Print the routine
    # if not args.run:
    #     info = yaml.safe_load(routine.yaml())
    #     output = {}
    #     output["name"] = info["name"]
    #     output["environment"] = info["environment"]
    #     output["algorithm"] = info["generator"]
    #     output["vocs"] = info["vocs"]
    #     output["initial_points"] = pd.DataFrame(info["initial_points"]).to_dict("list")
    #     output["critical_constraint_names"] = info["critical_constraint_names"]
    #     output["tags"] = info["tags"]
    #     output["script"] = info["script"]

    #     yprint(output)
    #     return

    # run_n_archive(routine, args.yes, False, args.verbose)
