from abc import ABC
from logging import warning
from typing import ClassVar, Dict, final, List, Optional

from pydantic import BaseModel, ConfigDict, Field, SerializeAsAny

from badger.errors import (
    BadgerEnvObsError,
    BadgerEnvVarError,
    BadgerInterfaceChannelError,
    BadgerNoInterfaceError,
)
from badger.interface import Interface


def validate_variable_names(func):
    def validate(cls, variable_names: List[str]):
        variable_names_invalid = [
            name for name in variable_names if name not in cls.variables
        ]
        if len(variable_names_invalid):
            raise BadgerEnvVarError(
                f"Variables {variable_names_invalid} not found in environment"
            )

        return func(cls, variable_names)

    return validate


def validate_observable_names(func):
    def validate(cls, observable_names: List[str]):
        observable_names_invalid = [
            name for name in observable_names if name not in cls.observables
        ]
        if len(observable_names_invalid):
            raise BadgerEnvObsError(
                f"Observables {observable_names_invalid} "
                + "not found in environment"
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
        validate_assignment=True,
        use_enum_values=True,
        arbitrary_types_allowed=True
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
        # Deal with variables defined in env
        variable_names_def = [v for v in variable_names if v in self.variables]
        variable_outputs_def = self.get_variables(variable_names_def)

        # Deal with tmp variables
        # Usually should be able to read from the interface
        variable_names_tmp = [v for v in variable_names if
                              v not in self.variables]

        # If no undefined variables
        if not len(variable_names_tmp):
            return variable_outputs_def

        # If no interface
        if self.interface is None:
            raise BadgerEnvVarError(
                f"Variables {variable_names_tmp} " +
                "do not exist in the environment!"
            )

        # Heads-up to the users that this behavior is not allowed for now
        err_msg = (
            f"Variables [{variable_names_tmp}] "
            + "not defined in the environment! "
            + "Getting them through interface is not allowed."
        )
        raise BadgerInterfaceChannelError(err_msg)

    # The reason for this method is we cannot know the bounds of a variable
    # that exists in interface but not defined in environment.
    # So we can only validate the setpoints for the defined variables
    @final
    @validate_setpoints
    def _set_variables_def(self, variable_inputs: Dict[str, float]):
        self.set_variables(variable_inputs)

    # Optimizer will only call this method to set variable values
    @final
    def _set_variables(self, variable_inputs: Dict[str, float]):
        # Deal with variables defined in env
        variable_inputs_def = dict(
            [v for v in variable_inputs.items() if v[0] in self.variables]
        )
        self._set_variables_def(variable_inputs_def)

        # Deal with tmp variables
        # Usually should be able to directly set to the interface
        variable_inputs_tmp = dict(
            [v for v in variable_inputs.items() if v[0] not in self.variables]
        )
        variable_names_tmp = list(variable_inputs_tmp.keys())

        # If no undefined variables
        if not len(variable_inputs_tmp):
            return

        # If no interface
        if self.interface is None:
            err_msg = (
                f"Variables [{variable_names_tmp}] "
                + "do not exist in the environment!"
            )
            raise BadgerEnvVarError(err_msg)

        # Heads-up to the users that this behavior is not allowed for now
        err_msg = (
            f"Variables [{variable_names_tmp}] "
            + "not defined in the environment! "
            + "Setting them through interface is not allowed."
        )
        raise BadgerInterfaceChannelError(err_msg)

    # Optimizer will only call this method to get observable values
    @final
    @validate_observable_names
    def _get_observables(self, observable_names: List[str]) -> Dict:
        return self.get_observables(observable_names)

    # Optimizer will only call this method to get variable bounds
    # Lazy loading -- read the bounds only when they are needed
    # TODO: considering cache validation (is it needed?)
    @final
    @validate_variable_names
    def _get_bounds(
        self, variable_names: Optional[List[str]] = None
    ) -> Dict[str, List[float]]:
        if variable_names is None:
            variable_names = self.variable_names

        variable_names_new = [
            name for name in variable_names if not len(self.variables[name])
        ]
        if len(variable_names_new):
            self.variables.update(self.get_bounds(variable_names_new))

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
