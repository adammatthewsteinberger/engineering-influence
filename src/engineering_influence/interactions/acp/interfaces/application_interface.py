# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for AcpApplication."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing import TextIO


class AcpApplicationInterface(ABC):
    """Serves the Agent Client Protocol: one JSON-RPC message per line on the given streams."""

    __slots__ = ()

    @abstractmethod
    def handle(self, message: Any) -> list[dict[str, Any]]:
        """The messages to send back for one incoming message: responses and notifications, in order."""

    @abstractmethod
    def progress_notices(self) -> list[dict[str, Any]]:
        """Notices for the runs whose status or stage changed since they were last reported."""

    @abstractmethod
    def serve(self, reader: TextIO, writer: TextIO, poll_seconds: float = 1.0) -> None:
        """Read messages until the input ends, and write each reply as one line.

        While the input is open, the runs of the sessions are followed every ``poll_seconds``, and their
        changes are written as notices between the replies.
        """
