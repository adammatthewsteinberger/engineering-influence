# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where a book run is in its life."""

from enum import StrEnum


class RunStatus(StrEnum):
    """A run is pending, running, parked for credit, or finished one way or another."""

    PENDING = "pending"
    RUNNING = "running"
    PARKED_CAPACITY = "parked_capacity"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
