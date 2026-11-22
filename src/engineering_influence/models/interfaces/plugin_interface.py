# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for Plugin."""

from abc import ABC, abstractmethod


class PluginInterface(ABC):
    """A plugin: a reviewed bundle of tool server definitions and skills."""

    __slots__ = ()

    @abstractmethod
    def identifier(self) -> str:
        """The name and version, as people write it: ``research_pack@1``."""

    @abstractmethod
    def server_names(self) -> tuple[str, ...]:
        """The names of the servers it describes, in order."""

    @abstractmethod
    def skill_names(self) -> tuple[str, ...]:
        """The names of the skills it carries, in order."""
