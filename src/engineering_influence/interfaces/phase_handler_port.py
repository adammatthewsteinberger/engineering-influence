"""Worker phase-handler port."""

from abc import ABC, abstractmethod
from typing import Any


class PhaseHandlerPort(ABC):
    """Handle one queued phase job for an external worker runtime."""

    @abstractmethod
    async def handle(self, job: Any) -> Any:
        """Return the runtime's success or parked outcome."""
