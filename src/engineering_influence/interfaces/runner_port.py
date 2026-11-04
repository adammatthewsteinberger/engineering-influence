"""Phase-runner port."""

from abc import ABC, abstractmethod


class RunnerPort(ABC):
    """Execute one phase with an already-loaded runner or skill."""

    @abstractmethod
    async def run(self, phase: str, context: dict[str, object]) -> str:
        """Return the phase artifact content."""
