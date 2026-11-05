"""Run every example as a real process against real sockets.

The API-facing examples are pointed at the real ASGI app served by uvicorn on a free port,
so they exercise the same HTTP path they use against the compose stack
(`examples/compose_smoke.sh` runs them there as well).
"""

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest
import uvicorn

from engineering_influence.infrastructure.in_memory_ledger import InMemoryLedger
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.observability.bootstrap_metrics import BootstrapMetrics
from engineering_influence.infrastructure.observability.context_var_correlation import (
    ContextVarCorrelation,
)
from engineering_influence.infrastructure.observability.correlating_queue import CorrelatingQueue
from engineering_influence.infrastructure.observability.toolchain_health_check import (
    ToolchainHealthCheck,
)
from engineering_influence.infrastructure.security.constant_time_api_key_verifier import (
    ConstantTimeApiKeyVerifier,
)
from engineering_influence.infrastructure.security.token_bucket_rate_limiter import (
    TokenBucketRateLimiter,
)
from engineering_influence.interaction.api.api_guard import ApiGuard
from engineering_influence.interaction.api.api_observability import ApiObservability
from engineering_influence.interaction.api.application import ApiApplication
from engineering_influence.services.readiness_probe import ReadinessProbe

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
API_KEY = "test-key-for-the-example-suite-0001"  # gitleaks:allow


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def run(command: list[str], env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
        env={**os.environ, **(env or {})},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


@pytest.fixture(scope="module")
def api_env() -> Iterator[dict[str, str]]:
    """Serve the real API on a free port, with the observability wiring `ei serve api` uses."""
    correlation = ContextVarCorrelation()
    readiness = ReadinessProbe((ToolchainHealthCheck(("python3",)),))
    app = ApiApplication(
        InMemoryLedger(),
        CorrelatingQueue(InMemoryQueue(), correlation),
        ApiGuard(
            ConstantTimeApiKeyVerifier([API_KEY]), TokenBucketRateLimiter(burst=50, per_second=50)
        ),
        ApiObservability(readiness, BootstrapMetrics(), correlation),
    ).build()
    port = free_port()
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    assert server.started, "the example API did not start"
    yield {"EI_BASE_URL": f"http://127.0.0.1:{port}", "EI_API_KEY": API_KEY}
    server.should_exit = True
    thread.join(timeout=10)


@pytest.mark.parametrize(
    ("script", "needles"),
    [
        ("api/start_pipeline.py", ["without a key: 401", "started: 200", "invalid body: 422"]),
        ("sdk/sync_client.py", ["sample-essay"]),
        ("sdk/async_client.py", ["sample-essay-3"]),
        (
            "observability/scrape.py",
            [
                "ready: 200 ready",
                "request id echoed: example-observe-0001",
                "ei_http_requests_total",
            ],
        ),
    ],
)
def test_api_example_runs(api_env: dict[str, str], script: str, needles: list[str]) -> None:
    output = run([sys.executable, str(EXAMPLES / script)], api_env).stdout
    for needle in needles:
        assert needle in output


@pytest.mark.skipif(shutil.which("curl") is None, reason="curl is not installed")
def test_curl_example_runs(api_env: dict[str, str]) -> None:
    output = run(["sh", str(EXAMPLES / "api" / "run.sh")], api_env).stdout
    assert "project_slug" in output
    assert "ei_http_requests_total" in output


def test_mcp_client_drives_the_stdio_server() -> None:
    output = run([sys.executable, str(EXAMPLES / "mcp" / "client.py")]).stdout
    assert "tool: start_pipeline" in output
    assert "sample-essay" in output


def test_cli_script_runs() -> None:
    output = run(
        ["sh", str(EXAMPLES / "cli" / "run.sh")],
        {"EI": f"{sys.executable} -m engineering_influence"},
    ).stdout
    assert "sample-essay" in output
    assert "exit status: 2" in output


def test_webhook_receiver_accepts_once_and_refuses_the_rest() -> None:
    port = free_port()
    env = {
        **os.environ,
        "EI_WEBHOOK_SECRET": "example-webhook-secret-0001",
        "EI_RECEIVER_PORT": str(port),
    }
    receiver = subprocess.Popen(
        [sys.executable, str(EXAMPLES / "webhooks" / "receiver.py")],
        env=env,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert receiver.stdout is not None
        assert "listening" in receiver.stdout.readline()
        output = run(
            [sys.executable, str(EXAMPLES / "webhooks" / "send_event.py")],
            {"EI_RECEIVER_URL": f"http://127.0.0.1:{port}/", **env},
        ).stdout
    finally:
        receiver.terminate()
        receiver.wait(timeout=10)
    assert "first delivery: 202 accepted" in output
    assert "replay of the same delivery: 409 replayed" in output
    assert "tampered body: 401 bad_signature" in output
    assert "an hour old: 401 stale_timestamp" in output


@pytest.mark.parametrize(
    ("scripts", "variable"),
    [
        (("webhooks/receiver.py", "webhooks/send_event.py"), "EI_WEBHOOK_SECRET"),
        (
            ("api/start_pipeline.py", "observability/scrape.py", "sdk/sync_client.py"),
            "EI_API_KEY",
        ),
    ],
)
def test_examples_refuse_to_run_without_their_credential(
    scripts: tuple[str, ...], variable: str
) -> None:
    env = {key: value for key, value in os.environ.items() if key != variable}
    for script in scripts:
        result = subprocess.run(
            [sys.executable, str(EXAMPLES / script)],
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
        )
        assert result.returncode == 2, script
        assert variable in result.stderr
