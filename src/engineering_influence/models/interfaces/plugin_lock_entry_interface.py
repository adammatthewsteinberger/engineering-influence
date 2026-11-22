# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PluginLockEntry."""

from abc import ABC, abstractmethod


class PluginLockEntryInterface(ABC):
    """One installed plugin, as the plugin lock records it."""

    __slots__ = ()

    @abstractmethod
    def identity(self) -> str:
        """The plugin as people write it, with its hash: ``research_pack@1:<hash>``."""
