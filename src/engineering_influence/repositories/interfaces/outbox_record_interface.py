# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for OutboxRecord."""

from abc import ABC


class OutboxRecordInterface(ABC):
    """Durable webhook intent whose delivery can be retried safely."""

    __slots__ = ()
