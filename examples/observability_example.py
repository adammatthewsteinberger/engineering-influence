"""Observability example: correlation ids, health probes and an authenticated /metrics scrape."""

from _sample import SampleGuard, SampleProject
from fastapi.testclient import TestClient

from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.observability.bootstrap_metrics import BootstrapMetrics
from engineering_influence.infrastructure.observability.context_var_correlation import (
    ContextVarCorrelation,
)
from engineering_influence.infrastructure.observability.correlating_queue import CorrelatingQueue
from engineering_influence.infrastructure.observability.json_logging_configurator import (
    JsonLoggingConfigurator,
)
from engineering_influence.infrastructure.observability.toolchain_health_check import (
    ToolchainHealthCheck,
)
from engineering_influence.interaction.api.api_observability import ApiObservability
from engineering_influence.interaction.api.application import ApiApplication
from engineering_influence.services.readiness_probe import ReadinessProbe


def main() -> None:
    JsonLoggingConfigurator("WARNING").configure()  # JSON lines on stderr
    correlation = ContextVarCorrelation()
    queue = InMemoryQueue()
    observability = ApiObservability(
        ReadinessProbe((ToolchainHealthCheck(("python3",)),)), BootstrapMetrics(), correlation
    )
    app = ApiApplication(
        InMemoryLedger(),
        CorrelatingQueue(queue, correlation),
        SampleGuard().build(),
        observability,
    ).build()
    client = TestClient(app)
    auth = {"Authorization": f"Bearer {SampleGuard.API_KEY}"}

    print("live:", client.get("/health/live").json()["status"])
    print("ready:", client.get("/health/ready").json()["status"])
    reply = client.post(
        "/v1/pipelines",
        json=SampleProject().load(),
        headers={**auth, "X-Request-ID": "example-request-0001"},
    )
    print("request id echoed:", reply.headers["x-request-id"])
    print("job carries id:", queue.jobs[0][1]["correlation_id"])
    print("metrics without a key:", client.get("/metrics").status_code)
    metrics = client.get("/metrics", headers=auth).text
    print("metrics lines:", [line for line in metrics.splitlines() if "http_requests" in line][-1])


if __name__ == "__main__":
    main()
