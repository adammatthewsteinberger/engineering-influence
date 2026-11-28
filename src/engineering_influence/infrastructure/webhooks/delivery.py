# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Signed outbound webhook delivery."""

import json
import time
from collections.abc import Callable

import httpx

from engineering_influence.contracts.webhook.v1.webhook_event_v1 import WebhookEventV1
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.webhooks.signer import WebhookSigner
from engineering_influence.interfaces.correlation_interface import CorrelationInterface
from engineering_influence.interfaces.outbound_url_policy_interface import (
    OutboundUrlPolicyInterface,
)
from engineering_influence.interfaces.webhook_delivery_interface import (
    WebhookDeliveryInterface,
)
from engineering_influence.models.trace_context import TraceContext


class WebhookDelivery(WebhookDeliveryInterface):
    """Send one signed, timestamped event to a destination the policy allows."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        url_policy: OutboundUrlPolicyInterface,
        clock: Callable[[], float] = time.time,
        correlation: CorrelationInterface | None = None,
    ) -> None:
        """Remember the HTTP client, the URL policy, the clock and the correlation for each delivery."""
        self._client = client
        self._url_policy = url_policy
        self._clock = clock
        self._correlation = correlation

    async def deliver(
        self,
        url: str,
        event_name: str,
        event_id: str,
        payload: dict[str, object],
        secret: bytes,
    ) -> int:
        """POST a signed versioned event and return the recipient status."""
        verdict = self._url_policy.check(url)
        if not verdict.accepted:
            raise ApplicationError(
                code="WEBHOOK_TARGET_REJECTED",
                message=f"webhook destination refused: {verdict.reason}",
            )
        event = WebhookEventV1(id=event_id, type=event_name, data=payload)
        body = json.dumps(
            event.model_dump(mode="json"), separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        timestamp = int(self._clock())
        signature = WebhookSigner(secret).sign_at(body, timestamp)
        headers = {
            "Content-Type": "application/json",
            "X-Engineering-Influence-Signature": signature,
            "X-Engineering-Influence-Timestamp": str(timestamp),
            "X-Engineering-Influence-Event": event_name,
            "X-Engineering-Influence-Event-Id": event_id,
        }
        correlation_id = self._correlation.current() if self._correlation else None
        if correlation_id:
            headers["X-Request-ID"] = correlation_id
            context = TraceContext.for_correlation_id(correlation_id)
            if context is not None:
                headers["traceparent"] = context.header()
        response = await self._client.post(url, content=body, headers=headers)
        return response.status_code
