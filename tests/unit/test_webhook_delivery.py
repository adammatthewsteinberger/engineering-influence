"""Outbound webhook delivery tests."""

import asyncio
import json

import httpx

from engineering_influence.interaction.webhooks import WebhookDelivery, WebhookSigner


def test_webhook_delivery_posts_signed_event() -> None:
    observed: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        observed["body"] = request.content
        observed["signature"] = request.headers["X-Engineering-Influence-Signature"]
        observed["event"] = request.headers["X-Engineering-Influence-Event"]
        return httpx.Response(202, request=request)

    async def run() -> int:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        status = await WebhookDelivery(client).deliver(
            "https://receiver.test/events",
            "pipeline.started",
            "evt-1",
            {"project_slug": "demo"},
            b"secret",
        )
        await client.aclose()
        return status

    assert asyncio.run(run()) == 202
    body = observed["body"]
    assert isinstance(body, bytes)
    assert json.loads(body) == {
        "data": {"project_slug": "demo"},
        "id": "evt-1",
        "type": "pipeline.started",
    }
    assert WebhookSigner(b"secret").verify(body, str(observed["signature"]))
    assert observed["event"] == "pipeline.started"
