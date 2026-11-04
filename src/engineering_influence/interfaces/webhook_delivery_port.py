# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Webhook delivery port."""

from abc import ABC, abstractmethod


class WebhookDeliveryPort(ABC):
    """Send one event to a signed webhook endpoint."""

    @abstractmethod
    async def deliver(
        self,
        url: str,
        event_name: str,
        event_id: str,
        payload: dict[str, object],
        secret: bytes,
    ) -> int:
        """Return the recipient HTTP status."""
