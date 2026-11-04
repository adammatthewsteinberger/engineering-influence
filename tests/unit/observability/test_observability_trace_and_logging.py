"""Trace context, correlation propagation and structured logging."""

import asyncio
import io
import json
import logging
from collections.abc import Iterator
from typing import Any

import pytest

from engineering_influence.domain.trace_context import TraceContext
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.observability.context_var_correlation import (
    ContextVarCorrelation,
)
from engineering_influence.infrastructure.observability.correlated_phase_handler import (
    CorrelatedPhaseHandler,
)
from engineering_influence.infrastructure.observability.correlating_queue import CorrelatingQueue
from engineering_influence.infrastructure.observability.json_logging_configurator import (
    JsonLoggingConfigurator,
)
from engineering_influence.interfaces.phase_handler_port import PhaseHandlerPort

TRACE = "4bf92f3577b34da6a3ce929d0e0e4736"
SPAN = "00f067aa0ba902b7"


def test_a_valid_traceparent_is_parsed() -> None:
    context = TraceContext.parse(f"00-{TRACE}-{SPAN}-01")

    assert context == TraceContext(TRACE, SPAN)
    assert context.header() == f"00-{TRACE}-{SPAN}-01"


@pytest.mark.parametrize(
    "header",
    [
        None,
        "",
        "garbage",
        f"01-{TRACE}-{SPAN}-01",
        f"00-{TRACE.upper()}-{SPAN}-01",
        f"00-{'0' * 32}-{SPAN}-01",
        f"00-{TRACE}-{'0' * 16}-01",
        f"00-{TRACE}-{SPAN}",
    ],
)
def test_malformed_traceparents_are_rejected(header: str | None) -> None:
    assert TraceContext.parse(header) is None


def test_correlation_prefers_the_trace_then_a_safe_request_id_then_a_new_one() -> None:
    assert TraceContext.resolve_correlation_id(f"00-{TRACE}-{SPAN}-01", "req-12345678") == TRACE
    assert TraceContext.resolve_correlation_id(None, "req-12345678") == "req-12345678"
    generated = TraceContext.resolve_correlation_id(None, None)
    assert len(generated) == 32 and generated != TraceContext.resolve_correlation_id(None, None)


@pytest.mark.parametrize(
    "hostile",
    [
        "short",
        "x" * 65,
        "a b c d e f g h",
        "id\nINJECTED log line",
        'q"uote-12345',
        "<script>12345",
    ],
)
def test_an_unsafe_request_id_is_replaced_not_echoed(hostile: str) -> None:
    resolved = TraceContext.resolve_correlation_id(None, hostile)

    assert resolved != hostile
    assert len(resolved) == 32


def test_only_a_trace_id_shaped_correlation_id_yields_a_traceparent() -> None:
    context = TraceContext.for_correlation_id(TRACE)

    assert context is not None and context.trace_id == TRACE and len(context.span_id) == 16
    assert TraceContext.for_correlation_id("req-12345678") is None
    assert TraceContext.for_correlation_id(None) is None
    assert TraceContext.for_correlation_id("0" * 32) is None


def test_correlation_scope_sets_and_clears_the_id() -> None:
    correlation = ContextVarCorrelation()

    assert correlation.current() is None
    with correlation.scope("abc-12345") as active:
        assert active == "abc-12345"
        assert correlation.current() == "abc-12345"
    assert correlation.current() is None


def test_queued_jobs_carry_a_copy_of_the_payload_with_the_correlation_id() -> None:
    inner = InMemoryQueue()
    correlation = ContextVarCorrelation()
    queue = CorrelatingQueue(inner, correlation)
    payload: dict[str, object] = {"project_slug": "demo"}

    with correlation.scope(TRACE):
        queue.enqueue("pipeline.thesis", payload)

    kind, queued = inner.jobs[0]
    assert kind == "pipeline.thesis"
    assert queued["correlation_id"] == TRACE
    assert str(queued["traceparent"]).startswith(f"00-{TRACE}-")
    assert payload == {"project_slug": "demo"}  # the ledger shares this dict


def test_a_non_trace_correlation_id_is_carried_without_a_traceparent() -> None:
    inner = InMemoryQueue()
    correlation = ContextVarCorrelation()

    with correlation.scope("req-12345678"):
        CorrelatingQueue(inner, correlation).enqueue("k", {})

    assert inner.jobs[0][1] == {"correlation_id": "req-12345678"}


def test_jobs_queued_outside_a_request_get_no_id() -> None:
    inner = InMemoryQueue()

    CorrelatingQueue(inner, ContextVarCorrelation()).enqueue("k", {"a": 1})

    assert inner.jobs[0][1] == {"a": 1}


class Job:
    """Minimal stand-in for a vibey job."""

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload


class SeenHandler(PhaseHandlerPort):
    """Records the correlation id active while it ran."""

    def __init__(self, correlation: ContextVarCorrelation) -> None:
        self._correlation = correlation
        self.seen: str | None = None

    async def handle(self, job: Any) -> Any:
        self.seen = self._correlation.current()
        return "done"


def test_the_worker_restores_the_id_the_job_was_queued_with() -> None:
    correlation = ContextVarCorrelation()
    inner = SeenHandler(correlation)

    result = asyncio.run(
        CorrelatedPhaseHandler(inner, correlation).handle(Job({"correlation_id": TRACE}))
    )

    assert result == "done"
    assert inner.seen == TRACE
    assert correlation.current() is None


@pytest.mark.parametrize("payload", [{}, {"correlation_id": 12345}])
def test_a_job_without_a_usable_id_still_gets_one(payload: dict[str, Any]) -> None:
    correlation = ContextVarCorrelation()
    inner = SeenHandler(correlation)

    asyncio.run(CorrelatedPhaseHandler(inner, correlation).handle(Job(payload)))

    assert inner.seen is not None and len(inner.seen) > 0


@pytest.fixture
def json_log() -> Iterator[io.StringIO]:
    stream = io.StringIO()
    root = logging.getLogger()
    saved_level, saved_handlers = root.level, list(root.handlers)
    JsonLoggingConfigurator("DEBUG", stream).configure()
    yield stream
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)


def records(stream: io.StringIO) -> list[dict[str, Any]]:
    return [json.loads(line) for line in stream.getvalue().splitlines() if line.strip()]


def test_logs_are_json_with_the_correlation_id(json_log: io.StringIO) -> None:
    with ContextVarCorrelation().scope(TRACE):
        logging.getLogger("demo").info("started", extra={"project": "demo"})

    record = records(json_log)[-1]
    assert record["message"] == "started"
    assert record["project"] == "demo"
    assert record["correlation_id"] == TRACE
    assert record["level"] == "INFO"


def test_secret_fields_are_masked(json_log: io.StringIO) -> None:
    logging.getLogger("demo").info(
        "call",
        extra={
            "api_key": "sk-live-1234567890",  # gitleaks:allow
            "authorization": "Bearer abcdefghij",
            "signature": "v1=deadbeef",
            "webhook_secret": "hunter2hunter2",
        },
    )

    text = json_log.getvalue()
    for secret in ("sk-live-1234567890", "abcdefghij", "deadbeef", "hunter2hunter2"):
        assert secret not in text


def test_configuring_twice_does_not_duplicate_lines(json_log: io.StringIO) -> None:
    JsonLoggingConfigurator("DEBUG", json_log).configure()
    JsonLoggingConfigurator("DEBUG", json_log).configure()

    logging.getLogger("demo").info("once")

    assert [r["message"] for r in records(json_log)].count("once") == 1


def test_the_level_is_honoured(json_log: io.StringIO) -> None:
    JsonLoggingConfigurator("WARNING", json_log).configure()

    logging.getLogger("demo").info("quiet")
    logging.getLogger("demo").warning("loud")

    messages = [r["message"] for r in records(json_log)]
    assert "loud" in messages and "quiet" not in messages
