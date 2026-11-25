# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PluginDownload."""

from abc import ABC


class PluginDownloadInterface(ABC):
    """A plugin file that was downloaded and checked: which entry, what it says, and where it was saved."""

    __slots__ = ()
