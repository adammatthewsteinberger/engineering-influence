# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for GateVerdict."""

from abc import ABC


class GateVerdictInterface(ABC):
    """Pass or fail for a named gate, with the issues behind the answer."""

    __slots__ = ()
