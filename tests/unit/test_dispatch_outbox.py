"""Outbox-to-webhook dispatch tests."""

import asyncio

from engineering_influence.interfaces.webhook_delivery_port import (
    WebhookDeliveryPort,
)
from engineering_influence.repositories import SqlModelOutbox
from engineering_influence.services.dispatch_outbox import DispatchOutbox


class DeliveryFake(WebhookDeliveryPort):
    """Returns configured statuses while recording deliveries."""

    def __init__(self, statuses: list[int]) -> None:
        self._statuses = statuses
        self.calls: list[tuple[str, str, str, dict[str, object], bytes]] = []

    async def deliver(
        self,
        url: str,
        event_name: str,
        event_id: str,
        payload: dict[str, object],
        secret: bytes,
    ) -> int:
        self.calls.append((url, event_name, event_id, payload, secret))
        return self._statuses[len(self.calls) - 1]


def test_dispatch_marks_only_successful_delivery() -> None:
    outbox = SqlModelOutbox()
    outbox.enqueue("evt-ok", "https://ok.test", "pipeline.started", {"slug": "ok"})
    outbox.enqueue("evt-fail", "https://fail.test", "pipeline.started", {"slug": "fail"})
    delivery = DeliveryFake([202, 503])

    acknowledged = asyncio.run(DispatchOutbox(outbox, delivery).dispatch(b"secret"))

    assert acknowledged == 1
    assert [event[0] for event in outbox.pending()] == ["evt-fail"]
    assert delivery.calls[0][4] == b"secret"
    outbox.close()
