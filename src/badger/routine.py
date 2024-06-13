import json
from copy import deepcopy
from typing import Optional, List, Any

import numpy as np
import pandas as pd
from pandas import DataFrame
from pydantic import ConfigDict, Field, model_validator, field_validator, \
    ValidationInfo, SerializeAsAny
from xopt import Xopt, VOCS, Evaluator
from xopt.generators import get_generator
from xopt.utils import get_local_region
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
    # Store relative to current params
    relative_to_current: Optional[bool] = Field(False)
    vrange_limit_options: Optional[dict] = Field(None)
    initial_point_actions: Optional[List] = Field(None)

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

                    # Add data one row at a time to avoid generator issues
                    for i in range(len(data["data"])):
                        row_df = data["data"].iloc[[i]]
                        data["generator"].add_data(row_df)

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

            # re-calculate the variable ranges and initial points
            # if relative to current is set
            try:
                relative_to_current = data["relative_to_current"]
            except KeyError:
                relative_to_current = False
            if relative_to_current:
                # Calculate the variable ranges
                limit_options = data["vrange_limit_options"]
                vnames = data["vocs"].variable_names
                var_curr = env._get_variables(vnames)

                vrange_dict = {}
                for v in configs_env['variables']:
                    vrange_dict.update(v)

                variables_updated = {}
                for name in vnames:
                    try:
                        limit_option = limit_options[name]
                    except KeyError:
                        continue

                    option_idx = limit_option['limit_option_idx']
                    if option_idx:
                        ratio = limit_option['ratio_full']
                        hard_bounds = vrange_dict[name]
                        delta = 0.5 * ratio * (hard_bounds[1] - hard_bounds[0])
                        bounds = [var_curr[name] - delta, var_curr[name] + delta]
                        bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
                        variables_updated[name] = bounds
                    else:
                        ratio = limit_option['ratio_curr']
                        hard_bounds = vrange_dict[name]
                        sign = np.sign(var_curr[name])
                        bounds = [var_curr[name] * (1 - 0.5 * sign * ratio),
                                  var_curr[name] * (1 + 0.5 * sign * ratio)]
                        bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
                        variables_updated[name] = bounds

                # Now update vocs with the variables_updated dict
                data['vocs'].variables = variables_updated

                # Calculate the initial points
                init_actions = data["initial_point_actions"]

                init_points = {k: [] for k in vnames}
                for action in init_actions:
                    if action['type'] == 'add_curr':
                        var_curr = env._get_variables(vnames)
                        for name in vnames:
                            init_points[name].append(var_curr[name])
                    elif action['type'] == 'add_rand':
                        var_curr = env._get_variables(vnames)
                        n_point = action['config']['n_points']
                        fraction = action['config']['fraction']
                        random_sample_region = get_local_region(
                            var_curr, data['vocs'], fraction=fraction)
                        random_points = data['vocs'].random_inputs(
                            n_point, custom_bounds=random_sample_region)
                        for point in random_points:
                            for name in vnames:
                                init_points[name].append(point[name])

                # Update the initial points in data
                data['initial_points'] = init_points

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
        if data_copy is not None:
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
