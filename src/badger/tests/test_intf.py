def test_find_intf():
    from badger.factory import get_intf, list_intf

    assert len(list_intf()) == 1

    _, configs = get_intf("test")
    assert configs["name"] == "test"
    assert configs["version"] == "1.0"


def test_get_params():
    from badger.factory import get_intf

    _, configs = get_intf("test")
    params = configs["params"]

    assert params == {"flag": 0}


def test_set_params():
    from badger.factory import get_intf

    Interface, _ = get_intf("test")
    intf = Interface(flag=1)

    assert intf.flag == 1


def test_get_values():
    from badger.factory import get_intf

    Interface, _ = get_intf("test")
    intf = Interface()

    channel_outputs = intf.get_values(["x1", "x2"])
    assert channel_outputs == {"x1": 0.5, "x2": 0.5}

    # Test single version
    value = intf.get_value("x3")
    assert value == 0.5


def test_set_values():
    from badger.factory import get_intf

    Interface, _ = get_intf("test")
    intf = Interface()

    channel_inputs = {"x1": 3, "x2": 4}
    intf.set_values(channel_inputs)
    channel_outputs = intf.get_values(["x1", "x2", "x3"])
    assert channel_outputs == {"x1": 3, "x2": 4, "x3": 0.5}

    # Test single version
    intf.set_value("x3", 5)
    value = intf.get_value("x3")
    assert value == 5


def test_recording():
    from badger.factory import get_intf

    Interface, _ = get_intf("test")
    intf = Interface()

    intf.set_values({"x1": 3, "x2": 4})
    intf.set_value("x3", 5)
    intf.get_values(["x1", "x2", "x3"])

    assert len(intf._logs) == 3
    record = intf._logs[0]
    assert record["action"] == "set_values"
    assert record["channel_inputs"] == {"x1": 3, "x2": 4}
    record = intf._logs[1]
    assert record["action"] == "set_values"
    assert record["channel_inputs"] == {"x3": 5}
    record = intf._logs[2]
    assert record["action"] == "get_values"
    assert record["channel_outputs"] == {"x1": 3, "x2": 4, "x3": 5}


# def test_run(mock_config_root):
#     from coolname import generate_slug
#     from badger.log import config_log
#     config_log()
#     from badger.factory import get_generator, get_env
#     from badger.utils import load_config, merge_params, config_list_to_dict
#     from badger.core import normalize_routine, run_routine

#     # Args
#     generator = 'silly'
#     generator_params = '{dimension: 2, max_iter: 10}'
#     env = 'silly'
#     env_params = None
#     config = os.path.join(mock_config_root, 'test.yaml')
#     save = False
#     yes = True
#     verbose = 2

#     # Get env params
#     _, configs_env = get_env(env)

#     # Get generator params
#     _, configs_generator = get_generator(generator)

#     # Normalize the generator and env params
#     params_env = load_config(env_params)
#     params_generator = load_config(generator_params)
#     params_env = merge_params(configs_env['params'], params_env)
#     params_generator = merge_params(configs_generator['params'], params_generator)

#     # Load routine configs
#     configs_routine = load_config(config)

#     # Compose the routine
#     routine = {
#         'name': save or generate_slug(2),
#         'generator': generator,
#         'env': env,
#         'generator_params': params_generator,
#         'env_params': params_env,
#         # env_vranges is an additional info for the normalization
#         # Will be removed after the normalization
#         'env_vranges': config_list_to_dict(configs_env['variables']),
#         'config': configs_routine,
#     }

#     # Sanity check and config normalization
#     routine = normalize_routine(routine)

#     run_routine(routine, yes, save, verbose)
