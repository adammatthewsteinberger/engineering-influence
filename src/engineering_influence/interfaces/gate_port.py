"""Gate-evaluation port."""

from abc import ABC, abstractmethod

from engineering_influence.domain.artifact import Artifact


class GatePort(ABC):
    """Evaluate deterministic or rubric-backed automatic gates."""

    @abstractmethod
    def evaluate(self, artifact: Artifact) -> bool:
        """Return whether an automatic gate accepts an artifact."""
