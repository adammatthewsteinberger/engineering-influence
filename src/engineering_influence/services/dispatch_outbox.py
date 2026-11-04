"""Application service connecting outbox persistence to webhook delivery."""

from engineering_influence.interfaces.outbox_port import (
    OutboxPort,
)
from engineering_influence.interfaces.webhook_delivery_port import (
    WebhookDeliveryPort,
)
from engineering_influence.services.interfaces.dispatch_outbox_interface import (
    DispatchOutboxInterface,
)


class DispatchOutbox(DispatchOutboxInterface):
    """Deliver pending events and acknowledge only successful responses."""

    def __init__(
        self,
        outbox: OutboxPort,
        delivery: WebhookDeliveryPort,
    ) -> None:
        self._outbox = outbox
        self._delivery = delivery

    async def dispatch(self, secret: bytes) -> int:
        acknowledged = 0
        for event_id, url, event_name, payload, _attempts in self._outbox.pending():
            status = await self._delivery.deliver(url, event_name, event_id, payload, secret)
            if 200 <= status < 300:
                self._outbox.mark_delivered(event_id)
                acknowledged += 1
        return acknowledged
