# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SseEventReader."""

from abc import ABC, abstractmethod


class SseEventReaderInterface(ABC):
    """Turns the bytes of a Server-Sent Events stream into the data of its message events."""

    __slots__ = ()

    @abstractmethod
    def feed(self, chunk: bytes) -> list[str]:
        """Take the next bytes; return the data of every message event they completed, in order.

        Raise ``ValueError`` for a line that is too long or is not UTF-8.
        """
