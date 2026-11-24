# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for Rubric."""

from abc import ABC


class RubricInterface(ABC):
    """The dimensions a book is judged on, the scale, and the thresholds a release must meet."""

    __slots__ = ()
