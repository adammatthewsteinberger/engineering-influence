"""REST observability end to end: correlation, counters, health, metrics, webhooks."""

import asyncio
import io
import json
import logging
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from engineering_influence.contracts.health_status import HealthStatus
from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.observability.context_var_correlation import (
    ContextVarCorrelation,
)
from engineering_influence.infrastructure.observability.correlating_queue import CorrelatingQueue
from engineering_influence.infrastructure.observability.json_logging_configurator import (
    JsonLoggingConfigurator,
)
from engineering_influence.infrastructure.security.constant_time_api_key_verifier import (
    ConstantTimeApiKeyVerifier,
)
from engineering_influence.infrastructure.security.public_https_url_policy import (
    PublicHttpsUrlPolicy,
)
from engineering_influence.infrastructure.security.token_bucket_rate_limiter import (
    TokenBucketRateLimiter,
)
from engineering_influence.interaction.api.api_guard import ApiGuard
from engineering_influence.interaction.api.api_observability import ApiObservability
from engineering_influence.interaction.api.application import ApiApplication
from engineering_influence.interaction.api.request_context_middleware import (
    RequestContextMiddleware,
)
from engineering_influence.interaction.webhooks import WebhookDelivery
from engineering_influence.interfaces.health_check_port import HealthCheckPort
from engineering_influence.interfaces.metrics_port import MetricsPort
from engineering_influence.services.readiness_probe import ReadinessProbe

KEY = "a-valid-api-key-0123456789"  # gitleaks:allow
AUTH = {"Authorization": f"Bearer {KEY}"}
PROJECT = {"slug": "demo", "title": "Demo", "postulates": ["Evidence first."], "stages": ["thesis"]}
TRACE = "4bf92f3577b34da6a3ce929d0e0e4736"


class CountingMetrics(MetricsPort):
    """Deterministic in-memory metrics."""

    def __init__(self) -> None:
        self.seen: dict[str, int] = {}

    def increment(self, name: str, amount: int = 1) -> None:
        self.seen[name] = self.seen.get(name, 0) + amount

    def counters(self) -> dict[str, int]:
        return dict(self.seen)

    def latencies(self) -> dict[str, dict[str, float]]:
        return {}


class Toggle(HealthCheckPort):
    """A dependency whose health the test controls."""

    def __init__(self, healthy: bool = True) -> None:
        self.healthy = healthy

    @property
    def name(self) -> str:
        return "rabbitmq"

    def check(self) -> HealthStatus:
        return HealthStatus(
            name="rabbitmq", healthy=self.healthy, detail=None if self.healthy else "down"
        )


class Harness:
    """An app with observability and handles on everything a test inspects."""

    def __init__(self) -> None:
        self.metrics = CountingMetrics()
        self.dependency = Toggle()
        self.correlation = ContextVarCorrelation()
        self.inner_queue = InMemoryQueue()
        guard = ApiGuard(
            ConstantTimeApiKeyVerifier([KEY]), TokenBucketRateLimiter(burst=1000, per_second=1000)
        )
        observability = ApiObservability(
            ReadinessProbe((self.dependency,)), self.metrics, self.correlation
        )
        application = ApiApplication(
            InMemoryLedger(),
            CorrelatingQueue(self.inner_queue, self.correlation),
            guard,
            observability,
        )
        self.app = application.build()
        self.app.add_api_route("/whoami", lambda: {"id": self.correlation.current()})

        def boom() -> None:
            raise RuntimeError("kaboom")

        self.app.add_api_route("/boom", boom)
        self.client = TestClient(self.app, raise_server_exceptions=False)


@pytest.fixture
def harness() -> Harness:
    return Harness()


def test_liveness_and_readiness_need_no_key(harness: Harness) -> None:
    assert harness.client.get("/health/live").json() == {"status": "alive"}
    assert harness.client.get("/health/ready").json() == {"status": "ready"}


def test_an_unready_dependency_returns_503_without_naming_it(harness: Harness) -> None:
    harness.dependency.healthy = False

    response = harness.client.get("/health/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert "rabbitmq" not in response.text


def test_metrics_require_a_key(harness: Harness) -> None:
    assert harness.client.get("/metrics").status_code == 401
    assert (
        harness.client.get("/metrics", headers={"Authorization": "Bearer wrong"}).status_code == 401
    )


def test_metrics_expose_counters_and_dependency_status(harness: Harness) -> None:
    harness.client.post("/v1/pipelines", json=PROJECT, headers=AUTH)
    harness.dependency.healthy = False

    response = harness.client.get("/metrics", headers=AUTH)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain; version=0.0.4")
    assert "ei_http_requests_total 1" in response.text
    assert "ei_http_status_2xx_total 1" in response.text
    assert 'ei_dependency_up{name="rabbitmq"} 0' in response.text
    assert "ei_ready 0" in response.text


def test_each_response_carries_a_correlation_id(harness: Harness) -> None:
    first = harness.client.get("/health/live").headers["x-request-id"]
    second = harness.client.get("/health/live").headers["x-request-id"]

    assert len(first) == 32 and first != second


def test_a_safe_inbound_request_id_is_kept(harness: Harness) -> None:
    response = harness.client.get("/whoami", headers={"X-Request-ID": "client-req-0001"})

    assert response.headers["x-request-id"] == "client-req-0001"
    assert response.json() == {"id": "client-req-0001"}


def test_an_inbound_traceparent_becomes_the_correlation_id(harness: Harness) -> None:
    response = harness.client.get(
        "/whoami",
        headers={"traceparent": f"00-{TRACE}-00f067aa0ba902b7-01", "X-Request-ID": "other-id-0001"},
    )

    assert response.headers["x-request-id"] == TRACE
    assert response.json() == {"id": TRACE}


def test_a_hostile_request_id_is_replaced(harness: Harness) -> None:
    response = harness.client.get("/whoami", headers={"X-Request-ID": "x" * 200})

    assert response.headers["x-request-id"] != "x" * 200
    assert len(response.headers["x-request-id"]) == 32


def test_the_id_reaches_the_queue_job(harness: Harness) -> None:
    harness.client.post(
        "/v1/pipelines",
        json=PROJECT,
        headers={**AUTH, "traceparent": f"00-{TRACE}-00f067aa0ba902b7-01"},
    )

    payload = harness.inner_queue.jobs[0][1]
    assert payload["correlation_id"] == TRACE
    assert str(payload["traceparent"]).startswith(f"00-{TRACE}-")


def test_requests_are_counted_by_outcome(harness: Harness) -> None:
    harness.client.post("/v1/pipelines", json=PROJECT, headers=AUTH)
    harness.client.post("/v1/pipelines", json=PROJECT)
    harness.client.get("/nope")

    seen = harness.metrics.counters()
    assert seen["http.requests"] == 3
    assert seen["http.status.2xx"] == 1
    assert seen["http.status.4xx"] == 2


def test_probes_and_metrics_do_not_inflate_the_counters(harness: Harness) -> None:
    harness.client.get("/health/live")
    harness.client.get("/health/ready")
    harness.client.get("/metrics", headers=AUTH)

    assert "http.requests" not in harness.metrics.counters()


def test_a_crashing_handler_is_counted_and_returns_500(harness: Harness) -> None:
    response = harness.client.get("/boom")

    assert response.status_code == 500
    assert harness.metrics.counters()["http.exceptions"] == 1
    assert harness.metrics.counters()["http.status.5xx"] == 1


def test_the_middleware_passes_non_http_scopes_straight_through(harness: Harness) -> None:
    with pytest.raises(WebSocketDisconnect), harness.client.websocket_connect("/no-such-socket"):
        pass

    assert "http.requests" not in harness.metrics.counters()


def call_asgi(middleware: RequestContextMiddleware, path: str) -> None:
    async def receive() -> dict[str, str]:
        return {"type": "http.request"}

    async def send(_: dict[str, Any]) -> None:
        return None

    scope = {"type": "http", "path": path, "headers": []}
    asyncio.run(middleware(scope, receive, send))  # type: ignore[arg-type]


class Crashing:
    """An ASGI app that fails before responding."""

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        raise RuntimeError("crashed")


@pytest.mark.parametrize(("path", "counted"), [("/health/ready", False), ("/v1/pipelines", True)])
def test_a_crash_is_counted_only_for_real_traffic(path: str, counted: bool) -> None:
    metrics = CountingMetrics()
    middleware = RequestContextMiddleware(Crashing(), ContextVarCorrelation(), metrics)

    with pytest.raises(RuntimeError, match="crashed"):
        call_asgi(middleware, path)

    assert ("http.exceptions" in metrics.counters()) is counted
    assert ("http.requests" in metrics.counters()) is counted


@pytest.fixture
def json_log() -> Iterator[io.StringIO]:
    stream = io.StringIO()
    root = logging.getLogger()
    saved_level, saved_handlers = root.level, list(root.handlers)
    JsonLoggingConfigurator("DEBUG", stream).configure()
    yield stream
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)


def test_request_logs_carry_the_correlation_id(harness: Harness, json_log: io.StringIO) -> None:
    harness.client.post(
        "/v1/pipelines", json=PROJECT, headers={**AUTH, "X-Request-ID": "client-req-0001"}
    )

    lines = [json.loads(line) for line in json_log.getvalue().splitlines() if line.strip()]
    http = [line for line in lines if line.get("operation") == "http_response"]
    assert http and all(line["correlation_id"] == "client-req-0001" for line in http)


def test_without_observability_there_are_no_extra_routes() -> None:
    guard = ApiGuard(ConstantTimeApiKeyVerifier([KEY]), TokenBucketRateLimiter(100, 100))
    client = TestClient(ApiApplication(InMemoryLedger(), InMemoryQueue(), guard).build())

    assert client.get("/health/live").status_code == 404
    assert "x-request-id" not in client.post("/v1/pipelines", json=PROJECT, headers=AUTH).headers


def deliver_with(correlation: ContextVarCorrelation, scope_id: str | None) -> httpx.Headers:
    captured: list[httpx.Headers] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.headers)
        return httpx.Response(200, request=request)

    async def run() -> None:
        client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        policy = PublicHttpsUrlPolicy(lambda _: ["93.184.216.34"])
        try:
            delivery = WebhookDelivery(client, policy, correlation=correlation)
            await delivery.deliver("https://r.example.com/", "x", "evt-1", {}, b"secret")
        finally:
            await client.aclose()

    if scope_id is None:
        asyncio.run(run())
    else:
        with correlation.scope(scope_id):
            asyncio.run(run())
    return captured[0]


def test_outbound_webhooks_carry_the_correlation_id() -> None:
    headers = deliver_with(ContextVarCorrelation(), TRACE)

    assert headers["x-request-id"] == TRACE
    assert headers["traceparent"].startswith(f"00-{TRACE}-")


def test_a_non_trace_id_is_sent_without_a_traceparent() -> None:
    headers = deliver_with(ContextVarCorrelation(), "client-req-0001")

    assert headers["x-request-id"] == "client-req-0001"
    assert "traceparent" not in headers


def test_webhooks_sent_outside_any_request_have_no_correlation_headers() -> None:
    headers = deliver_with(ContextVarCorrelation(), None)

    assert "x-request-id" not in headers
