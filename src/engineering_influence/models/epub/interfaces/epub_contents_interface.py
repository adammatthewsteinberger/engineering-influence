# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for EpubContents."""

from abc import ABC


class EpubContentsInterface(ABC):
    """Everything the verification checks read, loaded once."""

    __slots__ = ()
