import logging
import json
from copy import deepcopy
from typing import Any, List, Optional
import numpy as np
import pandas as pd
from pandas import DataFrame
from pydantic import (
    ConfigDict,
    Field,
    field_validator,
    model_validator,
    SerializeAsAny,
    ValidationInfo,
)
from xopt import Evaluator, VOCS, Xopt
from xopt.generators import get_generator
from xopt.utils import get_local_region
from xopt.generators.sequential import SequentialGenerator
from badger.utils import curr_ts
from badger.environment import BaseEnvironment, instantiate_env
from badger.factory import get_env

logger = logging.getLogger(__name__)


class Routine(Xopt):
    id: Optional[str] = Field(None)
    creation_ts: Optional[str] = Field(None)  # Timestamp of routine creation
    name: str
    description: Optional[str] = Field(None)
    environment: SerializeAsAny[BaseEnvironment]
    initial_points: Optional[DataFrame] = Field(None)
    critical_constraint_names: Optional[List[str]] = Field([])
    tags: Optional[List] = Field(None)
    script: Optional[str] = Field(None)
    # Store relative to current params
    relative_to_current: Optional[bool] = Field(False)
    vrange_limit_options: Optional[dict] = Field(None)
    vrange_hard_limit: Optional[dict] = Field({})  # override hard limits
    initial_point_actions: Optional[List] = Field(None)
    additional_variables: Optional[List[str]] = Field([])
    formulas: Optional[dict[str, dict[str, Any]]] = Field({})
    constraint_formulas: Optional[dict[str, dict[str, Any]]] = Field({})
    observable_formulas: Optional[dict[str, dict[str, Any]]] = Field({})
    # Other meta data
    badger_version: Optional[str] = Field(None)
    xopt_version: Optional[str] = Field(None)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @model_validator(mode="before")
    @classmethod
    def validate_model(cls, data: Any):
        logger.info("Validating Routine model from input data.")
        if isinstance(data, dict):
            logger.debug(f"Routine data dict received: {list(data.keys())}")
            # validate vocs
            if isinstance(data["vocs"], dict):
                logger.debug("Validating VOCS from dict.")
                data["vocs"] = VOCS(**data["vocs"])

            # validate generator
            if isinstance(data["generator"], dict):
                name = data["generator"].pop("name")
                logger.debug(f"Validating generator: {name}")
                generator_class = get_generator(name)
                data["generator"] = generator_class.model_validate(
                    {**data["generator"], "vocs": data["vocs"]}
                )

            elif isinstance(data["generator"], str):
                logger.debug(f"Validating generator from string: {data['generator']}")
                generator_class = get_generator(data["generator"])
                data["generator"] = generator_class.model_validate(
                    {"vocs": data["vocs"]}
                )

            if isinstance(data["generator"], SequentialGenerator):
                logger.debug("Setting SequentialGenerator is_active to False.")
                data["generator"].is_active = False

            # validate data (if it exists
            if "data" in data:
                if isinstance(data["data"], dict):
                    logger.debug("Validating and converting data to DataFrame.")
                    try:
                        data["data"] = pd.DataFrame(data["data"])
                    except IndexError:
                        data["data"] = pd.DataFrame(data["data"], index=[0])

                    data["data"].index = data["data"].index.astype(int)
                    data["data"].sort_index(inplace=True)

                    # Add data one row at a time to avoid generator issues
                    if isinstance(data["generator"], SequentialGenerator):
                        logger.debug("Setting data for SequentialGenerator.")
                        data["generator"].set_data(data["data"])
                    else:
                        logger.debug("Adding data to generator.")
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

            # create evaluator
            env = data["environment"]

            def evaluate_point(point: dict):
                logger.debug(f"Evaluating point: {point}")
                point = pd.Series(point).explode().to_dict()
                env.set_variables(point)
                obs = env.get_observables(data["vocs"].output_names)
                ts = curr_ts()
                obs["timestamp"] = ts.timestamp()
                obs["live"] = 1
                logger.debug(f"Evaluation result: {obs}")
                return obs

            data["evaluator"] = Evaluator(function=evaluate_point)

        return data

    @field_validator("initial_points", mode="before")
    def validate_data(cls, v, info: ValidationInfo):
        logger.debug("Validating initial_points field.")
        if isinstance(v, dict):
            try:
                v = pd.DataFrame(v)
            except IndexError:
                v = pd.DataFrame(v, index=[0])
        return v

    @property
    def sorted_data(self):
        logger.debug("Sorting routine data.")
        data_copy = deepcopy(self.data)
        if data_copy is not None:
            data_copy.index = data_copy.index.astype(int)
            data_copy.sort_index(inplace=True)
        return data_copy

    def json(self, **kwargs) -> str:
        logger.info("Serializing Routine to JSON.")
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
            "strict",
        ]
        for field in fields_to_be_removed:
            dict_result.pop(field, None)

        dict_result["environment"] = {"name": self.environment.name} | dict_result[
            "environment"
        ]
        try:
            dict_result["environment"]["interface"] = {
                "name": self.environment.interface.name
            } | dict_result["environment"]["interface"]
        except KeyError:
            pass
        except AttributeError:
            pass

        return json.dumps(dict_result)


def calculate_variable_bounds(limit_options, vocs, env):
    logger.info("Calculating variable bounds.")
    vnames = vocs.variable_names
    var_curr = env.get_variables(vnames)
    var_range = env.get_bounds(vnames)

    variables_updated = {}
    for name in vnames:
        try:
            limit_option = limit_options[name]
        except KeyError:
            logger.warning(f"No limit option for variable: {name}")
            continue

        option_idx = limit_option["limit_option_idx"]
        if option_idx:
            ratio = limit_option["ratio_full"]
            hard_bounds = var_range[name]
            delta = 0.5 * ratio * (hard_bounds[1] - hard_bounds[0])
            bounds = [var_curr[name] - delta, var_curr[name] + delta]
            bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
            logger.debug(f"Updated bounds for {name} (full): {bounds}")
            variables_updated[name] = bounds
        else:
            ratio = limit_option["ratio_curr"]
            hard_bounds = var_range[name]
            sign = np.sign(var_curr[name])
            bounds = [
                var_curr[name] * (1 - 0.5 * sign * ratio),
                var_curr[name] * (1 + 0.5 * sign * ratio),
            ]
            bounds = np.clip(bounds, hard_bounds[0], hard_bounds[1]).tolist()
            logger.debug(f"Updated bounds for {name} (curr): {bounds}")
            variables_updated[name] = bounds

    return variables_updated


def calculate_initial_points(init_actions, vocs, env):
    logger.info("Calculating initial points.")
    vnames = vocs.variable_names
    init_points = {k: [] for k in vnames}

    for action in init_actions:
        logger.debug(f"Processing initial point action: {action}")
        if action["type"] == "add_curr":
            var_curr = env.get_variables(vnames)
            for name in vnames:
                init_points[name].append(var_curr[name])
        elif action["type"] == "add_rand":
            var_curr = env.get_variables(vnames)
            n_point = action["config"]["n_points"]
            fraction = action["config"]["fraction"]
            random_sample_region = get_local_region(var_curr, vocs, fraction=fraction)
            random_points = vocs.random_inputs(
                n_point, custom_bounds=random_sample_region
            )
            for point in random_points:
                for name in vnames:
                    init_points[name].append(point[name])

    return init_points
