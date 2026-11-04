# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Gate kinds."""

from enum import StrEnum


class GateKind(StrEnum):
    """Whether a gate is evaluated automatically or by a person."""

    AUTO = "auto"
    HUMAN = "human"
