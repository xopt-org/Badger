import logging
import numpy as np
from typing import Callable
from pandas import DataFrame, concat
from pydantic import BaseModel
from xopt import Generator
from .environment import Environment

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
    from .factory import get_intf  # have to put here to avoid circular dependencies

    # Configure interface
    # TODO: figure out the correct logic
    # It seems that the interface should be given rather than
    # initialized here
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

    env = env_class(interface=intf, **configs['params'])

    return env



# __________________________Will be cut ________________________________

# The following functions are related to domain scaling
# TODO: consider combine them into a class and make it extensible
def list_scaling_func():
    return ['semi-linear', 'sinusoid', 'sigmoid']


def get_scaling_default_params(name):
    if name == 'semi-linear':
        default_params = {
            'center': 0.5,
            'range': 1,
        }
    elif name == 'sinusoid':
        default_params = {
            'center': 0.5,
            'period': 2,
        }
    elif name == 'sigmoid':
        default_params = {
            'center': 0.5,
            'lambda': 8,
        }
    else:
        raise Exception(f'scaling function {name} is not supported')

    return default_params


def get_scaling_func(configs):
    if not configs:  # fallback to default
        configs = {'func': 'semi-linear'}

    name = configs['func']
    params = configs.copy()
    del params['func']

    default_params = get_scaling_default_params(name)
    params = merge_params(default_params, params)

    if name == 'semi-linear':
        center, range = itemgetter('center', 'range')(params)

        def func(X):
            return np.clip((X - center) / range + 0.5, 0, 1)

    elif name == 'sinusoid':
        center, period = itemgetter('center', 'period')(params)

        def func(X):
            return 0.5 * np.sin(2 * np.pi / period * (X - center)) + 0.5

    elif name == 'sigmoid':
        center, lamb = itemgetter('center', 'lambda')(params)

        def func(X):
            return 1 / (1 + np.exp(-lamb * (X - center)))

    # TODO: consider remove this branch since it's useless
    else:
        raise Exception(f'scaling function {name} is not supported')

    return func