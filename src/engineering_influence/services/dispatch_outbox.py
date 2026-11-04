"""Application service connecting outbox persistence to webhook delivery."""

from engineering_influence.interaction.webhooks.interfaces.delivery_interface import (
    WebhookDeliveryInterface,
)
from engineering_influence.repositories.interfaces.outbox_repository_interface import (
    OutboxRepositoryInterface,
)
from engineering_influence.services.interfaces.dispatch_outbox_interface import (
    DispatchOutboxInterface,
)


class DispatchOutbox(DispatchOutboxInterface):
    """Deliver pending events and acknowledge only successful responses."""

    def __init__(
        self,
        outbox: OutboxRepositoryInterface,
        delivery: WebhookDeliveryInterface,
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
