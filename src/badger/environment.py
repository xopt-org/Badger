from abc import ABC
from logging import warning
from typing import ClassVar, Dict, final, List, Optional

from pydantic import BaseModel, ConfigDict, Field, SerializeAsAny

from badger.errors import (
    BadgerEnvObsError,
    BadgerEnvVarError,
    BadgerNoInterfaceError,
)
from badger.interface import Interface


def validate_observable_names(func):
    def validate(cls, observable_names: List[str]):
        observable_names_invalid = [
            name for name in observable_names if name not in cls.observables
        ]
        if len(observable_names_invalid):
            raise BadgerEnvObsError(
                f"Observables {observable_names_invalid} " + "not found in environment"
            )

        return func(cls, observable_names)

    return validate


def validate_setpoints(func):
    def validate(cls, variable_inputs: Dict[str, float]):
        _bounds = cls._get_bounds(list(variable_inputs.keys()))
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


class Environment(BaseModel, ABC):
    model_config = ConfigDict(
        validate_assignment=True, use_enum_values=True, arbitrary_types_allowed=True
    )

    # Class variables
    name: ClassVar[str] = Field(description="environment name")
    variables: ClassVar[Dict[str, List]]  # bounds list could be empty for var
    observables: ClassVar[List[str]]

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

    def get_bounds(self, variable_names: List[str]) -> Dict[str, List[float]]:
        return {}

    # Actions to preform after changing vars and before reading vars/obj
    def variables_changed(self, variables_input: Dict[str, float]):
        pass

    # Get current system states
    # If return is not None, the states would be saved at the start of each run
    # Should return a dict if not None
    def get_system_states(self) -> Optional[Dict]:
        return None

    # Shortcuts for getting/setting single variable
    def get_variable(self, variable_name):
        return self.get_variables([variable_name])[variable_name]

    def set_variable(self, variable_name, variable_value):
        return self.set_variables({variable_name: variable_value})

    def get_bound(self, variable_name):
        return self.get_bounds([variable_name])[variable_name]

    def search(self, keyword: str, callback: callable):
        return None

    ############################################################
    # Expert level of customization
    ############################################################

    # @model_serializer
    # def ser_model(self, **kwargs) -> Dict[str, Any]:
    #     default_dict = super().model_dump(**kwargs)
    #     default_dict["name"] = self.name

    #     return default_dict

    ############################################################
    # Should never be overridden
    ############################################################

    @final
    @property
    def variable_names(self):
        return [k for k in self.variables]

    # Optimizer will only call this method to get variable values
    @final
    def _get_variables(self, variable_names: List[str]) -> Dict:
        # We'll let the users handle the case when the variable is not defined
        variable_outputs = self.get_variables(variable_names)

        return variable_outputs

    # Optimizer will only call this method to set variable values
    @final
    @validate_setpoints
    def _set_variables(self, variable_inputs: Dict[str, float]):
        self.set_variables(variable_inputs)

    # Optimizer will only call this method to get observable values
    @final
    @validate_observable_names
    def _get_observables(self, observable_names: List[str]) -> Dict:
        return self.get_observables(observable_names)

    # Optimizer will only call this method to get variable bounds
    # Lazy loading -- read the bounds only when they are needed
    @final
    def _get_bounds(
        self, variable_names: Optional[List[str]] = None
    ) -> Dict[str, List[float]]:
        if variable_names is None:
            variable_names = self.variable_names

        # variable_names_unset also includes those defined but not initialized vars
        variable_names_unset = [
            name for name in variable_names if not len(self.variables.get(name, []))
        ]

        # Get bound one by one due to potential failure
        for name in variable_names_unset:
            try:
                bound = self.get_bound(name)
            except Exception as e:
                raise e

            if bound[1] <= bound[0]:
                raise BadgerEnvVarError(f"Invalid bound for {name}: {bound}")

            # TODO:The tmp vars will go into the class vars,
            # it might be better to use a different name
            self.variables.update({name: bound})

        return {k: self.variables[k] for k in variable_names}


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
