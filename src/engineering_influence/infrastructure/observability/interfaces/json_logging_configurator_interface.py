# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for JsonLoggingConfigurator."""

from abc import ABC, abstractmethod


class JsonLoggingConfiguratorInterface(ABC):
    """Replace the root handlers with one JSON handler; safe to call more than once."""

    __slots__ = ()

    @abstractmethod
    def configure(self) -> None:
        """Install the handler."""
