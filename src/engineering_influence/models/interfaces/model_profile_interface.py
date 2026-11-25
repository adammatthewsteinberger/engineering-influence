# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ModelProfile."""

from abc import ABC, abstractmethod


class ModelProfileInterface(ABC):
    """How to reach one model: which adapter, which server, and which variable holds the key."""

    __slots__ = ()

    @abstractmethod
    def requires_key(self) -> bool:
        """Whether a key must be present before the model can be called."""

    @abstractmethod
    def sends_key_in_clear(self) -> bool:
        """Whether the key would travel over plain http to a host that is not this machine."""
