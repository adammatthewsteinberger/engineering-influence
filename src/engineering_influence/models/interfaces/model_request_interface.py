# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ModelRequest."""

from abc import ABC


class ModelRequestInterface(ABC):
    """One call to a model: what to say and how much it may say back."""

    __slots__ = ()
