# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Inbound webhook verifier port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.contracts.security_verdict import SecurityVerdict


class WebhookVerifierInterface(ABC):
    """Authenticate one inbound signed delivery."""

    __slots__ = ()

    @abstractmethod
    def verify(self, body: bytes, signature: str | None, timestamp: str | None) -> SecurityVerdict:
        """Return the verdict for the raw body, its signature, and its timestamp."""
