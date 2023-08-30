import logging
import numpy as np
from typing import Callable
from pandas import DataFrame, concat
from pydantic import BaseModel
from xopt import Generator
from .environment import Environment
from .factory import get_intf 
from operator import itemgetter 
from .utils import range_to_str, yprint, merge_params, ParetoFront, norm, denorm, \
     parse_rule

logger = logging.getLogger(__name__)


class Routine(BaseModel):
    environment: Environment
    generator: Generator
    #initial_points: DataFrame
    
    # convenience properties    
    @property
    def vocs(self):
        """
        A property that returns the vocs of the generator attribute.

        Returns:
            self.generator.vocs : VOCS
        """
        return self.generator.vocs


def run_routine(
        routine: Routine,
        active_callback: Callable,
        generate_callback: Callable,
        evaluate_callback: Callable,
        environment_callback: Callable, 
        states_callback: Callable
        ) -> None:
    """
    Run the provided routine object using Xopt.

    Parameters
    ----------
    routine : Routine
        Routine object created by Badger GUI to run optimization.

    active_callback : Callable
        Callback function that returns a boolean denoting if optimization/evaluation
        should proceed.

    generate_callback : Callable
        Callback function called after generating candidate points that takes the form
        `f(generator: Generator, candidates: DataFrame)`.

    evaluate_callback : Callable
        Callback function called after evaluating points that takes the form `f(data:
        DataFrame)`.

    environment_callback : Callable
        Callback function called after 

    states_callback : Callable
        Callback function called after 
    """

    # initialize routine
    initialize_routine(routine, environment_callback)

    # get objects from routine
    initial_points = routine.initial_points
    environment = routine.environment
    generator = routine.generator

    # evaluate initial points
    result = evaluate_points(initial_points, environment, evaluate_callback)

    # add measurements to generator
    generator.add_data(result)

    # perform optimization
    while active_callback():
        # generate points to observe
        candidates = generator.generate()
        generate_callback(generator, candidates)

        # if still active evaluate the points and add to generator
        # check active_callback evaluate point
        if active_callback():
            result = evaluate_points(candidates, environment, evaluate_callback)

            # dump results to file

            # add data to generator
            generator.add_data(result)

        else:
            break

def evaluate_points(points: DataFrame, routine: Routine, callback: Callable) \
        -> DataFrame:
    """
    Evaluates points using the environment

    Parameters
    ----------
    points : DataFrame
    routine : Routine
    callback : Callable
    
    Returns
    -------
    evaluated_points : DataFrame
    """
    Routine.environment.set_variables(points)
    observables_points = Routine.environment.get_observables(Routine.vocs)    
    evaluated_points = concat(points, observables_points)
    
    callback() # make optional 

    return evaluated_points

def initialize_routine(routine: Routine, callback: Callable) -> None:
    """
    Initializes the routine, including the environment

    Parameters
    ----------
    routine: Routine
    """

    routine.environment.initialize()

    callback(routine.environment) # check this line 

def instantiate_env(env_class, configs, manager=None):
    """
    Instatiate the environment as defined by the user.

    Parameters
    ----------
    env_class :
    configs :
    manager : 
    
    Returns
    -------
    environment :

    """
    try:
        intf_name = configs['interface'][0]
    except KeyError:
        intf_name = None
    except Exception as e:
        logger.warning(e)
        intf_name = None

    if intf_name is not None:
        if manager is None:
            Interface, _ = get_intf(intf_name)
            intf = Interface()
        else:
            intf = manager.Interface()
    else:
        intf = None

    environment = env_class(interface=intf, **configs['params'])

    return environment
