# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for signing and verifying webhook payloads."""

from abc import ABC, abstractmethod


class WebhookSignerInterface(ABC):
    """HMAC signing used by outbound delivery and inbound verification."""

    __slots__ = ()

    @abstractmethod
    def sign(self, payload: bytes) -> str:
        """Return the versioned signature header value for the bare payload."""

    @abstractmethod
    def verify(self, payload: bytes, signature: str) -> bool:
        """Constant-time verify a versioned signature header."""

    @abstractmethod
    def sign_at(self, payload: bytes, timestamp: int) -> str:
        """Sign ``<timestamp>.<payload>`` so a captured delivery cannot be replayed."""

    @abstractmethod
    def verify_at(self, payload: bytes, signature: str, timestamp: int) -> bool:
        """Constant-time verify a timestamp-bound signature."""
