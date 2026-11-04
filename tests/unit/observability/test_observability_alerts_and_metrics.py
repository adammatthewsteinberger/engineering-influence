"""Alert logging, forwarding and process metrics."""

import logging
from collections.abc import Iterator

import pytest
from vibey_bootstrap.alerts.dispatcher import drain_pending_alerts, reset_state
from vibey_bootstrap.tracing.decorators import traced

from engineering_influence.infrastructure.observability.bootstrap_alert_dispatcher import (
    BootstrapAlertDispatcher,
)
from engineering_influence.infrastructure.observability.bootstrap_metrics import BootstrapMetrics


@pytest.fixture
def clean_alert_state(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("AZURE_BOOTSTRAP_ALLOW_RESET", "1")
    reset_state()
    yield
    reset_state()


@pytest.mark.parametrize(
    ("severity", "level"),
    [("warn", logging.WARNING), ("error", logging.ERROR), ("critical", logging.CRITICAL)],
)
def test_every_alert_is_logged_at_its_own_level(
    clean_alert_state: None, caplog: pytest.LogCaptureFixture, severity: str, level: int
) -> None:
    with caplog.at_level(logging.DEBUG):
        BootstrapAlertDispatcher().raise_alert(severity, "something broke", {"id": "1"}, "k")

    record = next(r for r in caplog.records if r.getMessage() == "alert: something broke")
    assert record.levelno == level
    assert record.alert_severity == severity  # type: ignore[attr-defined]
    assert record.dedup_key == "k"  # type: ignore[attr-defined]
    assert record.alert_context == {"id": "1"}  # type: ignore[attr-defined]


def test_alerts_are_forwarded_and_repeats_are_counted(clean_alert_state: None) -> None:
    dispatcher = BootstrapAlertDispatcher()

    dispatcher.raise_alert("error", "dead letter", {}, "dl:1")
    dispatcher.raise_alert("error", "dead letter", {}, "dl:1")

    pending = drain_pending_alerts()
    assert [(r.subject, r.count) for r in pending] == [("dead letter", 2)]


def test_context_keys_cannot_break_the_log_record(clean_alert_state: None) -> None:
    BootstrapAlertDispatcher().raise_alert("error", "x", {"name": "clash", "message": "clash"}, "k")


def test_unknown_severities_are_refused(clean_alert_state: None) -> None:
    with pytest.raises(ValueError):
        BootstrapAlertDispatcher().raise_alert("loud", "x", {}, "k")


def test_counters_accumulate() -> None:
    metrics = BootstrapMetrics()
    before = metrics.counters().get("test.hits", 0)

    metrics.increment("test.hits")
    metrics.increment("test.hits", 4)

    assert metrics.counters()["test.hits"] == before + 5


def test_latencies_report_numbers_for_traced_operations() -> None:
    @traced(operation="test.latency.op")
    def work() -> int:
        return 1

    work()
    stats = BootstrapMetrics().latencies()["test.latency.op"]

    assert stats["count"] >= 1
    assert {"errors", "p50", "p95", "p99", "max"} <= set(stats)
    assert "last_seen" not in stats
    assert all(isinstance(value, float) for value in stats.values())
