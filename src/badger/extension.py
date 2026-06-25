"""Base class for generator extensions — an alternative way to register
optimization algorithms outside the standard Xopt generator registry.
Third-party packages can subclass Extension to plug in custom algorithms."""

from abc import ABC, abstractmethod
from typing import List


class Extension(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def __init__(self):
        pass

    # List all available generators
    @abstractmethod
    def list_generator(self) -> List[str]:
        pass

    # Get config of an generator
    @abstractmethod
    def get_generator_config(self, name: str):
        pass

    # Run an optimization with an array-style evaluate function
    # and a configs dict
    @abstractmethod
    def optimize(self, evaluate, configs: dict):
        pass
