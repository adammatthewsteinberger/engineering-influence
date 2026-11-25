# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for PluginBundle."""

from abc import ABC


class PluginBundleInterface(ABC):
    """A plugin file that has been read: what it says, and the hash of exactly the bytes that said it."""

    __slots__ = ()
