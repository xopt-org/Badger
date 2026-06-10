from abc import ABC, abstractmethod
from typing import Any, Callable


class Extension(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError("Extension must implement name property")

    @abstractmethod
    def __init__(self) -> None:
        raise NotImplementedError("Extension must implement __init__ method")

    # List all available generators
    @abstractmethod
    def list_generator(self) -> list[str]:
        raise NotImplementedError("Extension must implement list_generator method")

    # Get config of an generator
    @abstractmethod
    def get_generator_config(self, name: str) -> dict[str, Any]:
        raise NotImplementedError(
            "Extension must implement get_generator_config method"
        )

    # Run an optimization with an array-style evaluate function
    # and a configs dict
    @abstractmethod
    def optimize(
        self, evaluate: Callable[[Any], Any], configs: dict[str, Any]
    ) -> dict[str, Any]:
        raise NotImplementedError("Extension must implement optimize method")
