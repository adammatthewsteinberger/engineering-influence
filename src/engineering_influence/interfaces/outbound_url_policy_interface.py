# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Outbound URL policy port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.contracts.security_verdict import SecurityVerdict


class OutboundUrlPolicyInterface(ABC):
    """Decide whether the service may call a caller-supplied URL."""

    __slots__ = ()

    @abstractmethod
    def check(self, url: str) -> SecurityVerdict:
        """Return the verdict for one destination URL."""
