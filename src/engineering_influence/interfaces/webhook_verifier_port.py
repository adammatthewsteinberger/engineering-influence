# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Inbound webhook verifier port."""

from abc import ABC, abstractmethod

from engineering_influence.contracts.security_verdict import SecurityVerdict


class WebhookVerifierPort(ABC):
    """Authenticate one inbound signed delivery."""

    @abstractmethod
    def verify(self, body: bytes, signature: str | None, timestamp: str | None) -> SecurityVerdict:
        """Return the verdict for the raw body, its signature, and its timestamp."""
