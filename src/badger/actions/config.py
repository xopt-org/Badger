import os
import logging

from badger.settings import (
    list_settings,
    read_value,
    write_value,
    BADGER_PATH_DICT,
    BADGER_CORE_DICT,
)
from badger.utils import yprint, convert_str_to_value

logger = logging.getLogger(__name__)


def config_settings(args):
    key = args.key

    if key is None:
        yprint(list_settings())
        return

    try:
        print("")
        try:
            return _config_path_var(key)
        except KeyError:
            return _config_core_var(key)
    except KeyError:
        pass
    except IndexError:
        pass
    except KeyboardInterrupt:
        return

    logger.error(f"{key} is not a valid Badger config key!")


def _config_path_var(var_name):
    display_name = BADGER_PATH_DICT[var_name]["display name"]
    desc = BADGER_PATH_DICT[var_name]["description"]

    print(f"=== Configure {display_name} ===")
    print(f"*** {desc} ***\n")
    while True:
        res = input(
            f"Please type in the path to the Badger {display_name} folder (S to skip, R to reset): \n"
        )
        if res == "S":
            break
        if res == "R":
            _res = input(
                f"The current value {read_value(var_name)} will be reset, proceed (y/[n])? "
            )
            if _res == "y":
                break
            elif (not _res) or (_res == "n"):
                print("")
                continue
            else:
                print(f"Invalid choice: {_res}")

        res = os.path.abspath(os.path.expanduser(res))
        if os.path.isdir(res):
            _res = input(f"Your choice is {res}, proceed ([y]/n)? ")
            if _res == "n":
                print("")
                continue
            elif (not _res) or (_res == "y"):
                break
            else:
                print(f"Invalid choice: {_res}")
        else:
            _res = input(f"{res} does not exist, do you want to create it ([y]/n)? ")
            if _res == "n":
                print("")
                continue
            elif (not _res) or (_res == "y"):
                os.makedirs(res)
                print(f"Directory {res} has been created")
                break
            else:
                print(f"Invalid choice: {_res}")

    if res == "R":
        write_value(var_name, None)
        print(f"You reset the Badger {display_name} folder setting")
    elif res != "S":
        write_value(var_name, res)
        print(f"You set the Badger {display_name} folder to {res}")


def _config_core_var(var_name):
    display_name = BADGER_CORE_DICT[var_name]["display name"]
    desc = BADGER_CORE_DICT[var_name]["description"]
    default = BADGER_CORE_DICT[var_name]["default value"]

    print(f"=== Configure {display_name} ===")
    print(f"*** {desc} ***\n")
    while True:
        res = input(
            f"Please type in the new value for {display_name} (S to skip, R to reset): \n"
        )
        if res == "S":
            break
        if res == "R":
            _res = input(
                f"The current value {read_value(var_name)} will be reset to {default}, proceed (y/[n])? "
            )
            if _res == "y":
                break
            elif (not _res) or (_res == "n"):
                print("")
                continue
            else:
                print(f"Invalid choice: {_res}")
        else:
            break

    if res == "R":
        write_value(var_name, default)
        print(f"You reset the {display_name} setting")
    elif res != "S":
        write_value(var_name, convert_str_to_value(res))
        print(f"You set {display_name} to {res}")
