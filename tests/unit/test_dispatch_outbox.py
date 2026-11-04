"""Outbox-to-webhook dispatch tests."""

import asyncio

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.alert_port import AlertPort
from engineering_influence.interfaces.metrics_port import MetricsPort
from engineering_influence.interfaces.webhook_delivery_port import (
    WebhookDeliveryPort,
)
from engineering_influence.repositories import SqlModelOutbox
from engineering_influence.services.dispatch_outbox import DispatchOutbox


class DeliveryFake(WebhookDeliveryPort):
    """Returns configured outcomes (a status, or an exception to raise) while recording calls."""

    def __init__(self, outcomes: list[int | Exception]) -> None:
        self._outcomes = outcomes
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
        outcome = self._outcomes[(len(self.calls) - 1) % len(self._outcomes)]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class MetricsFake(MetricsPort):
    """Counts increments in memory."""

    def __init__(self) -> None:
        self.seen: dict[str, int] = {}

    def increment(self, name: str, amount: int = 1) -> None:
        self.seen[name] = self.seen.get(name, 0) + amount

    def counters(self) -> dict[str, int]:
        return dict(self.seen)

    def latencies(self) -> dict[str, dict[str, float]]:
        return {}


class AlertsFake(AlertPort):
    """Records alerts."""

    def __init__(self) -> None:
        self.raised: list[tuple[str, str, dict[str, object], str]] = []

    def raise_alert(
        self, severity: str, subject: str, context: dict[str, object], dedup_key: str
    ) -> None:
        self.raised.append((severity, subject, context, dedup_key))


def build(
    outcomes: list[int | Exception], max_attempts: int = 5
) -> tuple[SqlModelOutbox, DeliveryFake, MetricsFake, AlertsFake, DispatchOutbox]:
    outbox = SqlModelOutbox()
    delivery = DeliveryFake(outcomes)
    metrics = MetricsFake()
    alerts = AlertsFake()
    return (
        outbox,
        delivery,
        metrics,
        alerts,
        DispatchOutbox(outbox, delivery, metrics, alerts, max_attempts),
    )


def test_dispatch_marks_only_successful_delivery() -> None:
    outbox, delivery, metrics, _, service = build([202, 503])
    outbox.enqueue("evt-ok", "https://ok.test", "pipeline.started", {"slug": "ok"})
    outbox.enqueue("evt-fail", "https://fail.test", "pipeline.started", {"slug": "fail"})

    acknowledged = asyncio.run(service.dispatch(b"secret"))

    assert acknowledged == 1
    assert [event[0] for event in outbox.pending()] == ["evt-fail"]
    assert delivery.calls[0][4] == b"secret"
    assert metrics.counters() == {"webhook.delivered": 1, "webhook.failed": 1}
    outbox.close()


def test_one_poisoned_event_does_not_block_the_events_behind_it() -> None:
    rejected = ApplicationError("WEBHOOK_TARGET_REJECTED", "destination refused")
    outbox, _, metrics, _, service = build([rejected, 202])
    outbox.enqueue("evt-bad", "http://10.0.0.1", "pipeline.started", {})
    outbox.enqueue("evt-good", "https://ok.test", "pipeline.started", {})

    acknowledged = asyncio.run(service.dispatch(b"secret"))

    assert acknowledged == 1
    assert [event[0] for event in outbox.pending()] == ["evt-bad"]
    assert metrics.counters()["webhook.failed"] == 1
    outbox.close()


def test_network_errors_are_isolated_too() -> None:
    outbox, _, _, _, service = build([ConnectionError("down"), 200])
    outbox.enqueue("evt-1", "https://a.test", "x", {})
    outbox.enqueue("evt-2", "https://b.test", "x", {})

    assert asyncio.run(service.dispatch(b"s")) == 1
    outbox.close()


def test_failed_attempts_are_counted_across_runs() -> None:
    outbox, _, _, _, service = build([500])
    outbox.enqueue("evt-1", "https://a.test", "x", {})

    asyncio.run(service.dispatch(b"s"))
    asyncio.run(service.dispatch(b"s"))

    assert outbox.pending()[0][4] == 2
    outbox.close()


def test_an_event_that_keeps_failing_is_dead_lettered_and_alerted_once() -> None:
    outbox, delivery, metrics, alerts, service = build([500], max_attempts=3)
    outbox.enqueue("evt-1", "https://a.test", "pipeline.started", {})

    for _ in range(5):
        asyncio.run(service.dispatch(b"s"))

    assert outbox.pending() == []
    assert len(delivery.calls) == 3
    assert metrics.counters()["webhook.dead_lettered"] == 1
    assert len(alerts.raised) == 1
    severity, subject, context, dedup_key = alerts.raised[0]
    assert severity == "error"
    assert "dead-lettered after 3 attempts" in subject
    assert context["event_id"] == "evt-1"
    assert dedup_key == "dead_letter:evt-1"
    assert "https://a.test" not in str(alerts.raised)
    outbox.close()


def test_a_successful_retry_is_not_dead_lettered() -> None:
    outbox, _, _, alerts, service = build([500, 500, 200], max_attempts=3)
    outbox.enqueue("evt-1", "https://a.test", "x", {})

    for _ in range(3):
        asyncio.run(service.dispatch(b"s"))

    assert outbox.pending() == []
    assert alerts.raised == []
    outbox.close()


def test_max_attempts_must_be_positive() -> None:
    with pytest.raises(ValueError, match="max_attempts"):
        build([200], max_attempts=0)
