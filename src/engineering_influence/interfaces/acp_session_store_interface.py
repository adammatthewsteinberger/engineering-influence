# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Store port for Agent Client Protocol sessions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.acp_session import AcpSession


class AcpSessionStoreInterface(ABC):
    """Keeps sessions across processes, so a client can load one after it reconnects."""

    __slots__ = ()

    @abstractmethod
    def get(self, session_id: str) -> AcpSession | None:
        """The stored session, or None if this agent never started it."""

    @abstractmethod
    def save(self, session: AcpSession) -> None:
        """Store the session, replacing any earlier state saved under its id."""
