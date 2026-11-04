# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Application service connecting outbox persistence to webhook delivery."""

import logging

from engineering_influence.interfaces.alert_port import AlertPort
from engineering_influence.interfaces.metrics_port import MetricsPort
from engineering_influence.interfaces.outbox_port import (
    OutboxPort,
)
from engineering_influence.interfaces.webhook_delivery_port import (
    WebhookDeliveryPort,
)
from engineering_influence.services.interfaces.dispatch_outbox_interface import (
    DispatchOutboxInterface,
)

_LOGGER = logging.getLogger(__name__)


class DispatchOutbox(DispatchOutboxInterface):
    """Deliver pending events, isolate failures, and dead-letter what keeps failing."""

    def __init__(
        self,
        outbox: OutboxPort,
        delivery: WebhookDeliveryPort,
        metrics: MetricsPort,
        alerts: AlertPort,
        max_attempts: int = 5,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self._outbox = outbox
        self._delivery = delivery
        self._metrics = metrics
        self._alerts = alerts
        self._max_attempts = max_attempts

    async def dispatch(self, secret: bytes) -> int:
        """One bad event must never block the events queued behind it."""
        acknowledged = 0
        for event_id, url, event_name, payload, _attempts in self._outbox.pending():
            try:
                status = await self._delivery.deliver(url, event_name, event_id, payload, secret)
                reason = f"status {status}"
            except Exception as error:  # noqa: BLE001 - isolate every delivery failure
                status = 0
                reason = type(error).__name__
            if 200 <= status < 300:
                self._outbox.mark_delivered(event_id)
                self._metrics.increment("webhook.delivered")
                acknowledged += 1
                continue
            self._record_failure(event_id, event_name, reason)
        return acknowledged

    def _record_failure(self, event_id: str, event_name: str, reason: str) -> None:
        attempts = self._outbox.mark_failed(event_id)
        self._metrics.increment("webhook.failed")
        _LOGGER.warning(
            "webhook delivery failed",
            extra={
                "event_id": event_id,
                "event_name": event_name,
                "reason": reason,
                "attempts": attempts,
            },
        )
        if attempts >= self._max_attempts:
            self._outbox.mark_dead(event_id)
            self._metrics.increment("webhook.dead_lettered")
            self._alerts.raise_alert(
                "error",
                f"webhook {event_name} dead-lettered after {attempts} attempts",
                {"event_id": event_id, "event_name": event_name, "reason": reason},
                f"dead_letter:{event_id}",
            )
