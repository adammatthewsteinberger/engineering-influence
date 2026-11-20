# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What one attempt to advance a run did."""

from enum import StrEnum


class AdvanceOutcome(StrEnum):
    """How a delivery of an advance message ended."""

    ADVANCED = "advanced"
    COMPLETED = "completed"
    RETRYING = "retrying"
    PARKED = "parked"
    FAILED = "failed"
    SKIPPED = "skipped"
    REPAIRED = "repaired"
