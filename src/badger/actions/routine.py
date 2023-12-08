import logging
logger = logging.getLogger(__name__)
import pandas as pd
import yaml
from ..utils import yprint


def show_routine(args):
    try:
        from ..db import load_routine, list_routine
        from .run import run_n_archive
    except Exception as e:
        logger.error(e)
        return

    # List routines
    if args.routine_name is None:
        routines = list_routine()[0]
        if routines:
            yprint(routines)
        else:
            print('No routine has been saved yet')
        return

    try:
        routine, _ = load_routine(args.routine_name)
        if routine is None:
            print(f'Routine {args.routine_name} not found')
            return
    except Exception as e:
        print(e)
        return

    # Print the routine
    if not args.run:
        info = yaml.safe_load(routine.yaml())
        output = {}
        output['name'] = info['name']
        output['environment'] = info['environment']
        output['algorithm'] = info['generator']
        output['vocs'] = info['vocs']
        output['initial_points'] = pd.DataFrame(
            info['initial_points']).to_dict('list')
        output['critical_constraint_names'] = info['critical_constraint_names']
        output['tags'] = info['tags']
        output['script'] = info['script']

        yprint(output)
        return

    run_n_archive(routine, args.yes, False, args.verbose)
