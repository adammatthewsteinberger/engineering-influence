# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SecurityVerdict."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.contracts.security_verdict import SecurityVerdict


class SecurityVerdictInterface(ABC):
    """Accepted, or rejected with a short stable reason code."""

    __slots__ = ()

    @classmethod
    @abstractmethod
    def accept(cls) -> SecurityVerdict:
        """Return the accepting verdict."""

    @classmethod
    @abstractmethod
    def reject(cls, reason: str) -> SecurityVerdict:
        """Return a rejecting verdict carrying a stable reason code."""
