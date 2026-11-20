# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The current time, from the system clock."""

from datetime import UTC, datetime

from engineering_influence.interfaces.clock_interface import ClockInterface


class SystemClock(ClockInterface):
    """Reports the wall-clock time in UTC."""

    def now(self) -> datetime:
        """The current moment, timezone-aware."""
        return datetime.now(UTC)
