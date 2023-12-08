from ..settings import read_value, BADGER_PATH_DICT, \
    reset_settings, mock_settings
from .config import _config_path_var


def self_check(args):

    # Reset Badger
    if args.reset:
        while True:
            _res = input(
                'Badger will be reset to the factory settings.\n'
                'Only the configurations and built-in plugins will be reset,\n'
                'your saved routines and data will not be touched.\n\n'
                'proceed (y/[n])? ')
            if _res == 'y':
                break
            elif (not _res) or (_res == 'n'):
                print('Reset cancelled.')
                return
            else:
                print(f'Invalid choice: {_res}')

        reset_settings()
        print('Badger has been reset to the factory settings.')
        return

    good = check_n_config_paths()
    if good:
        print('Badger is healthy!')


def check_n_config_paths():
    good = True

    issue_list = []

    for pname in BADGER_PATH_DICT.keys():
        if not read_value(pname):
            good = False
            # dname = BADGER_PATH_DICT[pname]['display name']
            # print(f'\n{dname} needs to be configured!')

            issue_list.append(pname)

    if not good:
        # Initial setup
        init = True
        while False:
            _res = input(
                'If this is your first time launching Badger, you should initialize it now.\n'
                'Proceed ([y]/n)? ')
            if (not _res) or (_res == 'y'):
                init = True
                break
            elif _res == 'n':
                init = False
                break
            else:
                print(f'Invalid choice: {_res}')

        if init:  # fill in the mock up settings so user can go immediately
            mock_settings()

            return True

        # Let the users deal with the issues
        while True:
            _res = input(
                f'\nFound {len(issue_list)} issue(s).\n'
                'Fix the issue(s) now ([y]/n)? ')
            if (not _res) or (_res == 'y'):
                break
            elif _res == 'n':
                return good
            else:
                print(f'Invalid choice: {_res}')

        for pname in issue_list:
            try:
                print('')
                _config_path_var(pname)
            except KeyboardInterrupt:
                pass

    return good
