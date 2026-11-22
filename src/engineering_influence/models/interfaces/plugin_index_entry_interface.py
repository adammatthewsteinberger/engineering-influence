# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PluginIndexEntry."""

from abc import ABC, abstractmethod


class PluginIndexEntryInterface(ABC):
    """One plugin a marketplace index lists: what it is called, where it is, and the hash it must have."""

    __slots__ = ()

    @abstractmethod
    def identifier(self) -> str:
        """The name and version, as people write it: ``research_pack@1``."""
