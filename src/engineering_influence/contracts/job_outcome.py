# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What happened to one processed job."""

from enum import StrEnum


class JobOutcome(StrEnum):
    """The terminal result of processing one job."""

    COMPLETED = "completed"
    AWAITING_GATE = "awaiting_gate"
    PIPELINE_COMPLETED = "pipeline_completed"
