# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Outbox dispatch service port."""

from abc import ABC, abstractmethod


class DispatchOutboxInterface(ABC):
    """Drain durable webhook intents through a delivery adapter."""

    @abstractmethod
    async def dispatch(self, secret: bytes) -> int:
        """Deliver pending events and return the number acknowledged."""
