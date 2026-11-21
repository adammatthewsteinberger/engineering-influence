# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ModelAnswer."""

from abc import ABC


class ModelAnswerInterface(ABC):
    """What a stage gets back from asking a model: an answer, or the best it could get and why not."""

    __slots__ = ()
