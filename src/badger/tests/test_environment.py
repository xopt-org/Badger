import json
import pytest
import numpy as np
from typing import Dict, List
from unittest.mock import Mock

from badger.environment import BaseEnvironment, Environment
from badger.errors import BadgerEnvVarError, BadgerNoInterfaceError
from badger.interface import Interface

# TEST_VOCS_BASE replacement for testing
TEST_VOCS_BASE = {
    "variables": {f"x{i}": [-1, 1] for i in range(4)},
    "objectives": {"f": "MINIMIZE"},
}


class TestEnvironment:
    """Test suite for the Environment classes and decorators."""

    def test_base_environment_abstract(self):
        """Test that BaseEnvironment cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseEnvironment()

    def test_basic_env(self):
        """Test basic environment functionality with custom implementation."""

        class TestEnv(BaseEnvironment):
            name = "test"
            variables = {f"x{i}": [-1, 1] for i in range(20)}
            observables = ["f"]

            my_flag: int = 0

            def get_variables(self, variable_names: List[str]) -> Dict[str, float]:
                return {name: 0.5 for name in variable_names}

            def set_variables(self, variable_inputs: Dict[str, float]):
                pass

            def get_observables(self, observable_names: List[str]) -> Dict[str, float]:
                return {ele: 1.0 for ele in observable_names}

        env = TestEnv()
        result = dict(env)
        assert result["my_flag"] == 0

        env.my_flag = 1
        result = dict(env)
        assert result["my_flag"] == 1

        result = json.loads(env.model_dump_json())
        assert result["my_flag"] == 1

    def test_environment_with_interface(self):
        """Test Environment class with interface."""
        # Create a mock interface
        mock_interface = Mock(spec=Interface)
        mock_interface.get_values.return_value = {"x1": 0.5, "f": 1.0}
        mock_interface.set_values.return_value = None
        mock_interface.reset_interface.return_value = None

        class TestEnv(Environment):
            name = "test"
            variables = {"x1": [-1, 1], "x2": [-2, 2]}
            observables = ["f", "g"]

        env = TestEnv(interface=mock_interface)

        # Test get_variables -- note due to the mock, it returns fixed values
        result = env.get_variables(["x1"])
        assert result == {"x1": 0.5, "f": 1.0}
        mock_interface.get_values.assert_called_with(["x1"])

        # Test set_variables
        env.set_variables({"x1": 0.3})
        mock_interface.set_values.assert_called_with({"x1": 0.3})

        # Test get_observables
        result = env.get_observables(["f"])
        assert result == {"x1": 0.5, "f": 1.0}

        # Test reset_environment
        env.reset_environment()
        mock_interface.reset_interface.assert_called_once()

    def test_environment_no_interface_error(self):
        """Test that Environment raises error when no interface is provided."""

        class TestEnv(Environment):
            name = "test"
            variables = {"x1": [-1, 1]}
            observables = ["f"]

        env = TestEnv()

        with pytest.raises(BadgerNoInterfaceError):
            env.get_variables(["x1"])

        with pytest.raises(BadgerNoInterfaceError):
            env.set_variables({"x1": 0.5})

        with pytest.raises(BadgerNoInterfaceError):
            env.get_observables(["f"])

    def test_bounds_validation(self):
        """Test bounds validation decorator."""

        class TestEnv(BaseEnvironment):
            name = "test"
            variables = {"x1": [-1, 1], "x2": [0, 10]}
            observables = ["f"]

            def get_variables(self, variable_names: List[str]) -> Dict[str, float]:
                return {name: 0.0 for name in variable_names}

            def set_variables(self, variable_inputs: Dict[str, float]):
                pass

            def get_observables(self, observable_names: List[str]) -> Dict[str, float]:
                return {name: 1.0 for name in observable_names}

            def get_bounds(self, variable_names: List[str]) -> dict[str, float]:
                # Test invalid bounds - should be caught by decorator
                return {"x1": [1, -1]}  # upper < lower

        env = TestEnv()

        with pytest.raises(
            BadgerEnvVarError, match="Lower bound greater than upper bound"
        ):
            env.get_bounds(["x1"])

    def test_setpoint_validation(self):
        """Test setpoint validation decorator."""

        class TestEnv(BaseEnvironment):
            name = "test"
            variables = {"x1": [-1, 1], "x2": [0, 10]}
            observables = ["f"]

            def get_variables(self, variable_names: List[str]) -> Dict[str, float]:
                return {name: 0.0 for name in variable_names}

            def set_variables(self, variable_inputs: Dict[str, float]):
                pass

            def get_observables(self, observable_names: List[str]) -> Dict[str, float]:
                return {name: 1.0 for name in observable_names}

        env = TestEnv()

        # Test valid setpoints
        env.set_variables({"x1": 0.5, "x2": 5.0})  # Should not raise

        # Test invalid setpoints
        with pytest.raises(
            BadgerEnvVarError, match="Input point for x1 is outside its bounds"
        ):
            env.set_variables({"x1": 2.0})  # Outside upper bound

        with pytest.raises(
            BadgerEnvVarError, match="Input point for x2 is outside its bounds"
        ):
            env.set_variables({"x2": -1.0})  # Outside lower bound

    def test_formula_processing(self):
        """Test formula processing decorator for observables."""

        class TestEnv(BaseEnvironment):
            name = "test"
            variables = {"x1": [-1, 1], "x2": [-1, 1]}
            observables = ["f", "g", "h"]

            def get_variables(self, variable_names: List[str]) -> Dict[str, float]:
                return {name: 0.0 for name in variable_names}

            def set_variables(self, variable_inputs: Dict[str, float]):
                pass

            def get_observables(self, observable_names: List[str]) -> Dict[str, float]:
                # Return base observables
                return {
                    name: {"f": 2.0, "g": 3.0, "h": 1.0}[name]
                    for name in observable_names
                }

        env = TestEnv()

        # Test formula with observables
        result = env.get_observables(["`f` + `g`", "h", "g"])

        # Should evaluate formula and include regular observable
        assert result["`f` + `g`"] == 5.0  # 2.0 + 3.0
        assert result["h"] == 1.0
        assert result["g"] == 3.0

        # Should not include the formula variables in output
        assert "f" not in result

    def test_convenience_methods(self):
        """Test convenience methods for single variable/observable operations."""

        class TestEnv(BaseEnvironment):
            name = "test"
            variables = {"x1": [-1, 1]}
            observables = ["f"]

            def get_variables(self, variable_names: List[str]) -> Dict[str, float]:
                return {name: 0.5 for name in variable_names}

            def set_variables(self, variable_inputs: Dict[str, float]):
                self._last_set = variable_inputs

            def get_observables(self, observable_names: List[str]) -> Dict[str, float]:
                return {name: 1.5 for name in observable_names}

        env = TestEnv()

        # Test get_variable
        assert env.get_variable("x1") == 0.5

        # Test set_variable
        env.set_variable("x1", 0.8)
        assert env._last_set == {"x1": 0.8}

        # Test get_observable
        assert env.get_observable("f") == 1.5

    def test_variable_names_property(self):
        """Test variable_names property for Environment class."""
        mock_interface = Mock(spec=Interface)

        class TestEnv(Environment):
            name = "test"
            variables = {"x1": [-1, 1], "x2": [0, 10], "x3": [-5, 5]}
            observables = ["f"]

        env = TestEnv(interface=mock_interface)
        assert set(env.variable_names) == {"x1", "x2", "x3"}

    def test_get_system_states(self):
        """Test get_system_states default implementation."""

        class TestEnv(BaseEnvironment):
            name = "test"
            variables = {"x1": [-1, 1]}
            observables = ["f"]

            def get_variables(self, variable_names: List[str]) -> Dict[str, float]:
                return {name: 0.0 for name in variable_names}

            def set_variables(self, variable_inputs: Dict[str, float]):
                pass

            def get_observables(self, observable_names: List[str]) -> Dict[str, float]:
                return {name: 1.0 for name in observable_names}

        env = TestEnv()
        assert env.get_system_states() == {}

    def test_search_not_implemented(self):
        """Test search method raises NotImplementedError by default."""

        class TestEnv(BaseEnvironment):
            name = "test"
            variables = {"x1": [-1, 1]}
            observables = ["f"]

            def get_variables(self, variable_names: List[str]) -> Dict[str, float]:
                return {name: 0.0 for name in variable_names}

            def set_variables(self, variable_inputs: Dict[str, float]):
                pass

            def get_observables(self, observable_names: List[str]) -> Dict[str, float]:
                return {name: 1.0 for name in observable_names}

        env = TestEnv()

        with pytest.raises(
            NotImplementedError, match="The search method is not implemented"
        ):
            env.search("test", lambda x: x)

    def test_env_in_routine(self):
        """Test environment integration with routine."""
        from badger.routine import Routine

        class TestEnv(BaseEnvironment):
            name = "test"
            variables = {f"x{i}": [-1, 1] for i in range(20)}
            observables = ["f"]

            my_flag: int = 0

            def get_variables(self, variable_names: List[str]) -> Dict[str, float]:
                return {name: 0.0 for name in variable_names}

            def set_variables(self, variable_inputs: Dict[str, float]):
                pass

            def get_observables(self, observable_names: List[str]) -> Dict[str, float]:
                return {ele: 1.0 for ele in observable_names}

        env = TestEnv()
        vocs = TEST_VOCS_BASE

        routine = Routine(
            name="test_routine", environment=env, vocs=vocs, generator="random"
        )
        result = json.loads(routine.json())
        assert result["environment"]["my_flag"] == 0

        routine.environment.my_flag = 1
        result = json.loads(routine.json())
        assert result["environment"]["my_flag"] == 1

    def test_env_from_get_env(self):
        """Test environment from factory function."""
        from badger.factory import get_env
        from badger.routine import Routine

        env, config = get_env("test")
        config.pop("interface")
        vocs = TEST_VOCS_BASE

        routine = Routine(
            name="test_routine",
            environment=env(**config),
            vocs=vocs,
            generator="random",
        )
        result = json.loads(routine.json())
        assert result["environment"]["flag"] == 0

        routine.environment.flag = 1
        result = json.loads(routine.json())
        assert result["environment"]["flag"] == 1

    def test_complex_formula_processing(self):
        """Test complex formula processing with numpy functions."""

        class TestEnv(BaseEnvironment):
            name = "test"
            variables = {"x1": [-1, 1], "x2": [-1, 1]}
            observables = ["data", "noise", "signal"]

            def get_variables(self, variable_names: List[str]) -> Dict[str, float]:
                return {name: 0.0 for name in variable_names}

            def set_variables(self, variable_inputs: Dict[str, float]):
                pass

            def get_observables(self, observable_names: List[str]) -> Dict[str, float]:
                # Return mock data for different observables
                data_map = {
                    "data": np.array([1, 2, 3, 4, 5]),
                    "noise": np.array([0.1, 0.2, 0.15, 0.05, 0.1]),
                    "signal": np.array([10, 20, 30, 40, 50]),
                }
                return {name: data_map.get(name, 1.0) for name in observable_names}

        env = TestEnv()

        # Test RMS formula
        result = env.get_observables(["rms(`noise`)"])
        expected_rms = np.sqrt(np.mean(np.array([0.1, 0.2, 0.15, 0.05, 0.1]) ** 2))
        assert np.isclose(result["rms(`noise`)"], expected_rms)

        # Test percentile formula
        result = env.get_observables(["percentile90(`signal`)"])
        expected_percentile = np.percentile(np.array([10, 20, 30, 40, 50]), 90)
        assert np.isclose(result["percentile90(`signal`)"], expected_percentile)

        # Test complex formula
        result = env.get_observables(["sqrt(mean(`data`**2)) + percentile95(`signal`)"])
        data_array = np.array([1, 2, 3, 4, 5])
        signal_array = np.array([10, 20, 30, 40, 50])
        expected = np.sqrt(np.mean(data_array**2)) + np.percentile(signal_array, 95)
        assert np.isclose(
            result["sqrt(mean(`data`**2)) + percentile95(`signal`)"], expected
        )

    def test_instantiate_env_function(self):
        """Test environment instantiation function."""
        from badger.environment import instantiate_env
        from badger.interface import Interface

        class TestEnv(Environment):
            name = "test"
            variables = {"x1": [-1, 1]}
            observables = ["f"]
            test_param: float = 1.0

        # Test with interface config
        configs = {"interface": ["test"], "params": {"test_param": 2.5}}

        # Mock the factory get_intf function
        import badger.factory

        original_get_intf = getattr(badger.factory, "get_intf", None)

        def mock_get_intf(name):
            mock_interface_class = Mock()
            mock_interface_class.return_value = Mock(spec=Interface)
            return mock_interface_class, {}

        badger.factory.get_intf = mock_get_intf

        try:
            env = instantiate_env(TestEnv, configs)
            assert env.test_param == 2.5
            assert env.interface is not None
        finally:
            # Restore original function
            if original_get_intf:
                badger.factory.get_intf = original_get_intf

        # Test without interface
        configs_no_intf = {"params": {"test_param": 3.0}}
        env = instantiate_env(TestEnv, configs_no_intf)
        assert env.test_param == 3.0
        assert env.interface is None
