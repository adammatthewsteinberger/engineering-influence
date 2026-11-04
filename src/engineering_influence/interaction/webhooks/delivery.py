"""Signed outbound webhook delivery."""

import json

import httpx

from engineering_influence.interaction.webhooks.signer import WebhookSigner
from engineering_influence.interfaces.webhook_delivery_port import (
    WebhookDeliveryPort,
)


class WebhookDelivery(WebhookDeliveryPort):
    """Send one signed event through an async HTTP client."""

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    async def deliver(
        self,
        url: str,
        event_name: str,
        event_id: str,
        payload: dict[str, object],
        secret: bytes,
    ) -> int:
        """POST a signed versioned event and return the recipient status."""
        body = json.dumps(
            {"id": event_id, "type": event_name, "data": payload},
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        signature = WebhookSigner(secret).sign(body)
        response = await self._client.post(
            url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-Engineering-Influence-Signature": signature,
                "X-Engineering-Influence-Event": event_name,
                "X-Engineering-Influence-Event-Id": event_id,
            },
        )
        return response.status_code
