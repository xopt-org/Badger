import pytest


def test_find_env():
    from badger.factory import list_env, get_env

    assert len(list_env()) == 2

    _, configs = get_env("test")
    assert configs["name"] == "test"
    assert configs["version"] == "1.0"


def test_get_params():
    from badger.factory import get_env

    _, configs = get_env("test")
    params = configs["params"]

    assert params == {"delay": 0.0, "flag": 0}


def test_set_params():
    from badger.factory import get_env, get_intf

    Interface, _ = get_intf("test")
    intf = Interface()

    # Test pass params only
    Environment, _ = get_env("test")
    env = Environment(flag=1)

    assert env.interface is None
    assert env.flag == 1

    # Test pass interface
    env = Environment(interface=intf)
    assert env.interface
    assert env.flag == 0


def test_list_variables():
    from badger.factory import get_env

    Environment, _ = get_env("test")
    env = Environment()

    variables = {f"x{i}": [-1, 1] for i in range(20)}
    assert env.variables == variables

    assert env.variable_names == list(variables.keys())


def test_list_observables():
    from badger.factory import get_env

    Environment, _ = get_env("test")
    env = Environment()

    assert env.observables == ["f", "c"]


def test_get_variables():
    from badger.factory import get_env, get_intf
    from badger.errors import (
        BadgerNoInterfaceError,
    )

    Interface, _ = get_intf("test")
    intf = Interface()

    # Without interface
    Environment, _ = get_env("test")
    env = Environment()

    with pytest.raises(BadgerNoInterfaceError):
        env._get_variables(["x1", "x2"])

    # With interface
    env.interface = intf

    variable_outputs = env._get_variables(["x1", "x2"])
    assert variable_outputs == {"x1": 0.5, "x2": 0.5}

    # Test getting variables not defined in env
    # with pytest.raises(Exception) as e:
    #     variable_outputs = env._get_variables(["x19", "x20"])

    # assert e.type == BadgerInterfaceChannelError
    # assert "x19" not in str(e.value)
    # assert "x20" in str(e.value)
    # assert "Getting them through interface is not allowed" in str(e.value)


def test_set_variables():
    from badger.factory import get_env, get_intf
    from badger.errors import (
        BadgerEnvVarError,
        BadgerNoInterfaceError,
    )

    Interface, _ = get_intf("test")
    intf = Interface()

    # Without interface
    Environment, _ = get_env("test")
    env = Environment()

    variable_inputs = {"x1": 1, "x2": -1}
    with pytest.raises(BadgerNoInterfaceError):
        env._set_variables(variable_inputs)

    # With interface
    env.interface = intf

    env._set_variables(variable_inputs)
    variable_outputs = env._get_variables(["x1", "x2"])
    assert variable_outputs == {"x1": 1, "x2": -1}

    # Test setting variables not defined in env
    # variable_inputs_undef = {"x21": 1, "x22": -1}
    # with pytest.raises(Exception) as e:
    #     env._set_variables(variable_inputs_undef)

    # assert e.type == BadgerInterfaceChannelError
    # assert "x21" in str(e.value)
    # assert "Setting them through interface is not allowed" in str(e.value)

    # Test setting variables out of range
    variable_inputs_out_range = {"x1": 0, "x2": -2}
    with pytest.raises(Exception) as e:
        env._set_variables(variable_inputs_out_range)

    assert e.type == BadgerEnvVarError  # getting crazy w/ custom error
    assert "x1" not in str(e.value)
    assert "x2" in str(e.value)
    assert "outside its bounds" in str(e.value)

    variable_outputs = env._get_variables(["x1", "x2"])
    assert variable_outputs == {"x1": 1, "x2": -1}  # values shouldn't change


def test_get_observables():
    from badger.factory import get_env, get_intf
    from badger.errors import BadgerEnvObsError, BadgerNoInterfaceError

    Interface, _ = get_intf("test")
    intf = Interface()

    # Without interface
    Environment, _ = get_env("test")
    env = Environment()

    with pytest.raises(BadgerNoInterfaceError):
        env._get_observables(["f"])

    # With interface
    env.interface = intf

    variable_outputs = env._get_observables(["f"])
    assert variable_outputs == {"f": 0.5}

    variable_inputs = {"x1": 1, "x2": -1}
    env._set_variables(variable_inputs)
    variable_outputs = env._get_observables(["f"])
    assert variable_outputs == {"f": 6.5}

    # Test getting observables not defined in env
    with pytest.raises(Exception) as e:
        variable_outputs = env._get_observables(["g"])

    assert e.type == BadgerEnvObsError
    assert "g" in str(e.value)
    assert "not found in environment" in str(e.value)
