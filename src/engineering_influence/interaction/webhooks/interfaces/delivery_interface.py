"""Webhook delivery port."""

from abc import ABC, abstractmethod


class WebhookDeliveryInterface(ABC):
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
