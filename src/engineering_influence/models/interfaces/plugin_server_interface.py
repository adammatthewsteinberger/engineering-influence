# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PluginServer."""

from abc import ABC, abstractmethod


class PluginServerInterface(ABC):
    """A tool server a plugin names: a definition to review, never something that is run for you."""

    __slots__ = ()

    @abstractmethod
    def remote(self) -> bool:
        """Whether the server is reached at an address instead of started as a command."""

    @abstractmethod
    def tools_add_arguments(self) -> tuple[str, ...]:
        """The arguments after ``ei`` that lock this server: what a person would type, and review."""
