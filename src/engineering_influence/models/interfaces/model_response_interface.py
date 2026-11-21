# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ModelResponse."""

from abc import ABC, abstractmethod


class ModelResponseInterface(ABC):
    """What a model sent back."""

    __slots__ = ()

    @abstractmethod
    def was_truncated(self) -> bool:
        """True when the model hit its output cap before it finished."""

    @abstractmethod
    def was_refused(self) -> bool:
        """True when the model declined to answer."""
