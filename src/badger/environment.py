from abc import abstractmethod
from logging import warning
from typing import Any, ClassVar, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, SerializeAsAny
from pydantic._internal._model_construction import ModelMetaclass
from badger.errors import (
    BadgerEnvVarError,
    BadgerNoInterfaceError,
)
from badger.formula import extract_variable_keys, interpret_expression
from badger.interface import Interface


def validate_setpoints(func):
    def validate(cls, variable_inputs: Dict[str, float]):
        _bounds = cls.get_bounds(list(variable_inputs.keys()))
        for name, value in variable_inputs.items():
            lower = _bounds[name][0]
            upper = _bounds[name][1]

            if value > upper or value < lower:
                raise BadgerEnvVarError(
                    f"Input point for {name} is outside "
                    + f"its bounds {_bounds[name]}"
                )

        return func(cls, variable_inputs)

    return validate


def process_formulas(func):
    """
    Decorator function that wraps get_observables method
    to process formulas if they exist in the observable names.
    """

    def process(cls, observable_names: List[str]) -> Dict[str, float]:
        # get the list of observable names needed by themselves and any formulas
        formula_observables = []
        basic_observables = []
        formulas = []
        for name in observable_names:
            if any(ele in name for ele in ["`"]):
                # If the name contains a formula, extract the variables
                # and add them to the list of observable names needed
                formulas.append(name)
                formula_observables += list(extract_variable_keys(name))

            else:
                # If the name is a regular observable, just add it
                basic_observables.append(name)

        # pass to the original method
        all_observables_needed = set(basic_observables + formula_observables)
        observable_outputs = func(cls, list(all_observables_needed))

        # for each observable name, if it is a formula,
        # evaluate the formula and add it to the output
        for name in formulas:
            observable_outputs[name] = interpret_expression(name, observable_outputs)

        # pop data used in formulas
        for name in formula_observables:
            if name in observable_outputs:
                # remove the variable from the output
                # as it is not needed anymore
                observable_outputs.pop(name)

        # add raw data tracking
        # observable_outputs.update({"raw_data": raw_data})

        return observable_outputs

    return process


def validate_bounds(func):
    def validate(cls, variable_names: List[str]):
        bounds = func(cls, variable_names)

        for name, bound in bounds.items():
            if not isinstance(bound, (list, tuple)) or len(bound) != 2:
                raise BadgerEnvVarError(
                    f"Bounds for {name} must be a list or tuple of length 2."
                )
            lower, upper = bound
            if not (
                isinstance(lower, (int, float)) and isinstance(upper, (int, float))
            ):
                raise BadgerEnvVarError(f"Bounds for {name} must be numeric.")
            if lower > upper:
                raise BadgerEnvVarError(
                    f"Lower bound greater than upper bound for {name}: {bound}"
                )

        return bounds

    return validate


class EnvMeta(ModelMetaclass):
    def __new__(mcs, name, bases, namespace):
        # Wrap get_bounds with validate_bounds if defined
        if "get_bounds" in namespace:
            namespace["get_bounds"] = validate_bounds(namespace["get_bounds"])
        # Wrap get_observables with process_formulas if defined
        if "get_observables" in namespace:
            namespace["get_observables"] = process_formulas(
                namespace["get_observables"]
            )
        # Wrap set_variables with validate_setpoints if defined
        if "set_variables" in namespace:
            namespace["set_variables"] = validate_setpoints(namespace["set_variables"])
        return super().__new__(mcs, name, bases, namespace)


class BaseEnvironment(BaseModel, metaclass=EnvMeta):
    """
    Base class for all environments in Badger.
    This class defines the API for environments and provides
    methods to interact with them.
    """

    model_config = ConfigDict(
        validate_assignment=True, use_enum_values=True, arbitrary_types_allowed=True
    )
    name: ClassVar[str] = Field(description="environment name")
    variables: ClassVar[Dict[str, List]]  # bounds list could be empty for var
    observables: ClassVar[List[str]]

    @abstractmethod
    def get_variables(self, variable_names: List[str]) -> Dict[str, float]:
        """
        Get the values of the specified variables from the environment.

        Parameters
        ----------
        variable_names : List[str]
            A list of variable names to retrieve from the environment.

        Returns
        -------
        Dict[str, float]
            A dictionary mapping variable names to their values.
        """
        pass

    @abstractmethod
    def set_variables(self, variable_inputs: Dict[str, float]):
        """
        Set the values of the specified variables in the environment.

        Parameters
        ----------
        variable_inputs : Dict[str, float]
            A dictionary mapping variable names to their values.
        """
        pass

    @abstractmethod
    def get_observables(
        self, observable_names: List[str]
    ) -> Dict[str, float | List[float]]:
        """
        Get the values of the specified observables from the environment.

        The observables can be returned as a dictionary of float or a list of floats.
        If the observable is a list of floats, it is assumed to be a time series or a vector of values.

        Parameters
        ----------
        observable_names : List[str]
            A list of observable names to retrieve from the environment.

        Returns
        -------
        Dict[str, float | List[float]]
            A dictionary mapping observable names to their values.

        """
        pass

    def reset_environment(self):
        """
        Reset the environment to its initial state.
        This method is called at the start of each run.
        """
        pass

    def get_system_states(self) -> Dict[str, Any]:
        """
        Get the current system states from the environment.
        This method is called to retrieve the current state of the environment.

        Returns
        -------
        Dict[str, Any]
            A dictionary containing the current system states.
        """
        return {}

    def get_bounds(self, variable_names: List[str]) -> dict[str, float]:
        """
        Get the bounds for the specified variables in the environment.
        The bounds are returned as a dictionary with variable names as keys
        and a list of [lower_bound, upper_bound] as values.

        Parameters
        ----------
        variable_names : List[str]
            A list of variable names for which to retrieve bounds.

        """
        return {name: self.variables[name] for name in variable_names}

    def search(self, keyword: str, callback: callable):
        """
        Search for a keyword in the environment and call the callback function
        with the results.

        Parameters
        ----------
        keyword : str
            The keyword to search for in the environment.
        callback : callable
            A callback function to call with the search results.
            The callback should accept a single argument, which is the search result.
        """

        raise NotImplementedError(
            "The search method is not implemented in this environment."
        )

    # convience methods
    def get_variable(self, variable_name: str) -> float:
        """
        Get the value of a single variable from the environment.

        Parameters
        ----------
        variable_name : str
            The name of the variable to retrieve.

        Returns
        -------
        float
            The value of the specified variable.
        """
        return self.get_variables([variable_name])[variable_name]

    def set_variable(self, variable_name: str, value: float):
        """
        Set the value of a single variable in the environment.

        Parameters
        ----------
        variable_name : str
            The name of the variable to set.
        value : float
            The value to set for the specified variable.
        """
        self.set_variables({variable_name: value})

    def get_observable(self, observable_name: str) -> float:
        """
        Get the value of a single observable from the environment.

        Parameters
        ----------
        observable_name : str
            The name of the observable to retrieve.

        Returns
        -------
        float
            The value of the specified observable.
        """
        return self.get_observables([observable_name])[observable_name]


class Environment(BaseEnvironment):
    # Interface
    interface: Optional[SerializeAsAny[Interface]] = None
    # Put all other env params here
    # params: float = Field(..., description='Example env parameter')

    ############################################################
    # Optional methods to inherit
    ############################################################

    def get_variables(self, variable_names: List[str]) -> Dict:
        if not self.interface:
            raise BadgerNoInterfaceError

        return self.interface.get_values(variable_names)

    def set_variables(self, variable_inputs: Dict[str, float]):
        if not self.interface:
            raise BadgerNoInterfaceError

        return self.interface.set_values(variable_inputs)

    def get_observables(self, observable_names: List[str]) -> Dict:
        if not self.interface:
            raise BadgerNoInterfaceError

        return self.interface.get_values(observable_names)

    def reset_environment(self):
        if self.interface:
            return self.interface.reset_interface()

    @property
    def variable_names(self):
        return [k for k in self.variables]


def instantiate_env(env_class, configs, manager=None):
    # Configure interface
    # TODO: figure out the correct logic
    # It seems that the interface should be given rather than
    # initialized here
    from badger.factory import get_intf

    try:
        intf_name = configs["interface"][0]
    except KeyError:
        intf_name = None
    except Exception as e:
        warning(e)
        intf_name = None

    if intf_name is not None:
        if manager is None:
            Interface, _ = get_intf(intf_name)
            intf = Interface()
        else:
            intf = manager.Interface()
    else:
        intf = None

    env = env_class(interface=intf, **configs["params"])

    return env
