from badger.settings import init_settings
import os
import logging

from badger.utils import yprint, convert_str_to_value

logger = logging.getLogger(__name__)


def config_settings(args):
    config_singleton = init_settings()
    key = args.key

    if key is None:
        yprint(config_singleton.list_settings())
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
    config_singleton = init_settings()

    is_path = config_singleton.read_is_path(var_name)

    if not is_path:
        raise KeyError

    display_name = config_singleton.read_display_name(var_name)
    desc = config_singleton.read_description(var_name)

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
                f"The current value {config_singleton.read_value(var_name)} will be reset, proceed (y/[n])? "
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
        config_singleton.write_value(var_name, None)
        print(f"You reset the Badger {display_name} folder setting")
    elif res != "S":
        config_singleton.write_value(var_name, res)
        print(f"You set the Badger {display_name} folder to {res}")


def _config_core_var(var_name):
    config_singleton = init_settings()

    display_name = config_singleton.get_section("core")[var_name]["display name"]
    desc = config_singleton.get_section("core")[var_name]["description"]
    default = config_singleton.get_section("core")[var_name]["default value"]

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
                f"The current value {config_singleton.read_value(var_name)} will be reset to {default}, proceed (y/[n])? "
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
        config_singleton.write_value(var_name, default)
        print(f"You reset the {display_name} setting")
    elif res != "S":
        config_singleton.write_value(var_name, convert_str_to_value(res))
        print(f"You set {display_name} to {res}")
