from badger.settings import init_settings, mock_settings
from badger.actions.config import _config_path_var


def self_check(args):
    config = init_settings()
    # Reset Badger

    if args.reset:
        while True:
            _res = input(
                "Badger will be reset to the factory settings.\n"
                "Only the configurations and built-in plugins will be reset,\n"
                "your saved routines and data will not be touched.\n\n"
                "proceed (y/[n])? "
            )
            if _res == "y":
                break
            elif (not _res) or (_res == "n"):
                print("Reset cancelled.")
                return
            else:
                print(f"Invalid choice: {_res}")

        config.reset_settings()
        print("Badger has been reset to the factory settings.")
        return

    good = check_n_config_paths()
    if good:
        print("Badger is healthy!")


def check_n_config_paths(config_filepath=None):
    if config_filepath is not None:
        config = init_settings(config_filepath)
    else:
        config = init_settings()

    good = True
    all_bad = True  # if all config paths are empty, we'll suggest initialization
    issue_list = []

    for pname, pvalue in config._config.model_dump(by_alias=True).items():
        if config.read_value(pname) is None:
            good = False
            issue_list.append(pname)
        else:
            if pvalue["is_path"]:
                all_bad = False

    if not good:
        if all_bad:
            # Initial setup
            init = True
            while True:
                _res = input(
                    "It looks like this is your first time launching Badger. Would you like to initialize it now?\n"
                    "Proceed ([y]/n): "
                )
                if (not _res) or (_res == "y"):
                    init = True
                    break
                elif _res == "n":
                    init = False
                    break
                else:
                    print(f"Invalid choice: {_res}")

            if init:  # fill in the mock up settings so user can go immediately
                mock_settings()

                return True

        # Let the users deal with the issues
        while True:
            _res = input(
                f"\nFound {len(issue_list)} issue(s).\nFix the issue(s) now ([y]/n)? "
            )
            if (not _res) or (_res == "y"):
                break
            elif _res == "n":
                return good
            else:
                print(f"Invalid choice: {_res}")

        fixed = True
        for pname in issue_list:
            try:
                print("")
                success = _config_path_var(pname)
                if not success:
                    fixed = False
                # TODO potential keyError here
            except KeyboardInterrupt:
                pass

        return fixed

    return good
