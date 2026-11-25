# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for RevisionPass."""

from abc import ABC


class RevisionPassInterface(ABC):
    """One pass of editing over every chapter: what it is called, what it reads and writes, and how far it may change a chapter."""

    __slots__ = ()
