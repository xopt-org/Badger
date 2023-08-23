import logging
import numpy as np
from typing import Callable
from pandas import DataFrame, concat
from pydantic import BaseModel
from xopt import Generator
from .environment import Environment

logger = logging.getLogger(__name__)


class Routine(BaseModel):
    environment: Environment
    generator: Generator
    initial_points: DataFrame
    
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
        evaluate_callback: Callable
        ) -> None:
    """
    Run the provided routine object using Xopt.

    Pseudo code:
    Initialize environment
    Evaluate initial point(s)
    while(active_callback()):
        generate candidates to run
        if active_callback():
            evaluate candidates
            save data
        else:
            break

    Parameters
    ----------
    routine : Routine
        Routine object created by Badger GUI to run optimization.

    evaluate_callback : Callable
        Callback function called after evaluating points that takes the form `f(data:
        DataFrame)`.

    generate_callback : Callable
        Callback function called after generating candidate points that takes the form
        `f(generator: Generator, candidates: DataFrame)`.

    active_callback : Callable
        Callback function that returns a boolean denoting if optimization/evaluation
        should proceed.
    """

    # initialize routine
    initialize_routine(routine)

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

def initialize_routine(routine: Routine) -> None:
    """
    Initializes the routine, including the environment

    Parameters
    ----------
    routine: Routine
    """
    routine.environment.initialize()
