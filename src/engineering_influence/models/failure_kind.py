# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How a failed model call should be handled."""

from enum import StrEnum


class FailureKind(StrEnum):
    """Retry a transient failure, park a run on a capacity failure, stop on anything else."""

    TRANSIENT = "transient"
    CAPACITY = "capacity"
    UNRECOVERABLE = "unrecoverable"
