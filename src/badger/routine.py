import json
from copy import deepcopy
from typing import Optional, List, Any

import pandas as pd
from pandas import DataFrame
from pydantic import ConfigDict, Field, model_validator, field_validator, \
    ValidationInfo, SerializeAsAny
from xopt import Xopt, VOCS, Evaluator
from xopt.generators import get_generator
from badger.utils import curr_ts
from badger.environment import Environment, instantiate_env


class Routine(Xopt):

    name: str
    description: Optional[str] = Field(None)
    environment: SerializeAsAny[Environment]
    initial_points: Optional[DataFrame] = Field(None)
    critical_constraint_names: Optional[List[str]] = Field([])
    tags: Optional[List] = Field(None)
    script: Optional[str] = Field(None)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data: Any):
        from badger.factory import get_env

        if isinstance(data, dict):
            # validate vocs
            if isinstance(data["vocs"], dict):
                data["vocs"] = VOCS(**data["vocs"])

            # validate generator
            if isinstance(data["generator"], dict):
                name = data["generator"].pop("name")
                generator_class = get_generator(name)
                data["generator"] = generator_class.model_validate(
                    {**data["generator"], "vocs": data["vocs"]}
                )
            elif isinstance(data["generator"], str):
                generator_class = get_generator(data["generator"])

                data["generator"] = generator_class.model_validate(
                    {"vocs": data["vocs"]}
                )

            # validate data (if it exists
            if "data" in data:
                if isinstance(data["data"], dict):
                    try:
                        data["data"] = pd.DataFrame(data["data"])
                    except IndexError:
                        data["data"] = pd.DataFrame(data["data"], index=[0])

                    data["generator"].add_data(data["data"])

            # instantiate env
            if isinstance(data["environment"], dict):
                # TODO: Actually we need this interface info, but
                # should be put somewhere else (in parallel with env?)
                try:
                    del data["environment"]["interface"]
                except KeyError:  # no interface at all, which is good
                    pass
                name = data["environment"].pop("name")
                env_class, configs_env = get_env(name)
                configs_env["params"] |= data["environment"]
                data["environment"] = instantiate_env(env_class, configs_env)
            else:  # should be an instantiated env already
                pass

            # create evaluator
            env = data["environment"]

            def evaluate_point(point: dict):
                # sanitize inputs
                point = pd.Series(point).explode().to_dict()
                env._set_variables(point)
                obs = env._get_observables(data["vocs"].output_names)

                ts = curr_ts()
                obs['timestamp'] = ts.timestamp()

                return obs

            data["evaluator"] = Evaluator(function=evaluate_point)

        return data

    @field_validator("initial_points", mode="before")
    def validate_data(cls, v, info: ValidationInfo):
        if isinstance(v, dict):
            try:
                v = pd.DataFrame(v)
            except IndexError:
                v = pd.DataFrame(v, index=[0])

        return v

    @property
    def sorted_data(self):
        data_copy = deepcopy(self.data)
        data_copy.index = data_copy.index.astype(int)
        data_copy.sort_index(inplace=True)

        return data_copy

    def json(self, **kwargs) -> str:
        """Handle custom serialization of environment"""

        result = super().json(**kwargs)
        dict_result = json.loads(result)

        # Remove extra fields
        fields_to_be_removed = [
            "dump_file",
            "evaluator",
            "max_evaluations",
            "serialize_inline",
            "serialize_torch",
            "strict"
        ]
        for field in fields_to_be_removed:
            dict_result.pop(field, None)

        dict_result["environment"] = {"name": self.environment.name} |\
            dict_result["environment"]
        try:
            dict_result["environment"]["interface"] = {
                "name": self.environment.interface.name} |\
                dict_result["environment"]["interface"]
        except KeyError:
            pass
        except AttributeError:
            pass

        return json.dumps(dict_result)
