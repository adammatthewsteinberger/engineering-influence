# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ManuscriptError."""

from abc import ABC


class ManuscriptErrorInterface(ABC):
    """The manuscript breaks a rule of the print pipeline."""

    __slots__ = ()
