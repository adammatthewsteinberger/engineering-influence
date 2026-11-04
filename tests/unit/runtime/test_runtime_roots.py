"""The two composition roots: the API and the worker."""

import asyncio
import logging
import os
import signal
import sys
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

import pytest
import uvicorn
from fastapi.testclient import TestClient

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.observability.process_crash_hooks import ProcessCrashHooks
from engineering_influence.infrastructure.observability.worker_heartbeat import WorkerHeartbeat
from engineering_influence.infrastructure.rabbitmq_job_consumer import RabbitMqJobConsumer
from engineering_influence.interfaces.secret_provider_port import SecretProviderPort
from engineering_influence.repositories.sqlmodel_ledger import SqlModelLedger
from engineering_influence.runtime.api_runtime import ApiRuntime
from engineering_influence.runtime.app_settings import AppSettings
from engineering_influence.runtime.worker_runtime import WorkerRuntime

KEY = "a-valid-api-key-0123456789"  # gitleaks:allow
AUTH = {"Authorization": f"Bearer {KEY}"}
PROJECT = {
    "slug": "demo",
    "title": "Demo",
    "postulates": ["Evidence first."],
    "stages": ["thesis", "book"],
}
UNREACHABLE_BROKER = "amqp://svc:rabbitpw@127.0.0.1:1/"


class Secrets(SecretProviderPort):
    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = values

    def require(self, name: str) -> str:
        if name not in self._values:
            raise ApplicationError("SECRET_MISSING", f"required secret {name} is not configured")
        return self._values[name]


@pytest.fixture
def api_runtime(request: pytest.FixtureRequest) -> Any:
    """Build an ApiRuntime and close its database pool afterwards."""

    def make(settings: AppSettings, secrets: SecretProviderPort) -> ApiRuntime:
        runtime = ApiRuntime(settings, secrets)
        request.addfinalizer(runtime.close)
        return runtime

    return make


def settings_for(tmp_path: Path, **overrides: Any) -> AppSettings:
    return AppSettings(f"sqlite:///{tmp_path / 'ei.db'}", UNREACHABLE_BROKER, **overrides)


@pytest.fixture
def process_state() -> Iterator[None]:
    root = logging.getLogger()
    saved_handlers, saved_level = list(root.handlers), root.level
    saved_hook, saved_flag = sys.excepthook, ProcessCrashHooks._installed
    ProcessCrashHooks._installed = False
    yield
    root.handlers[:] = saved_handlers
    root.setLevel(saved_level)
    sys.excepthook = saved_hook
    ProcessCrashHooks._installed = saved_flag


def test_the_api_serves_probes_and_guards_everything_else(tmp_path: Path, api_runtime: Any) -> None:
    app = api_runtime(settings_for(tmp_path), Secrets({"EI_API_KEYS": KEY})).build_app()
    client = TestClient(app)

    assert client.get("/health/live").status_code == 200
    assert client.get("/health/ready").status_code == 503  # the broker is unreachable
    assert client.post("/v1/pipelines", json=PROJECT).status_code == 401
    assert client.get("/metrics").status_code == 401
    metrics = client.get("/metrics", headers=AUTH).text
    assert 'ei_dependency_up{name="rabbitmq"} 0' in metrics
    assert "database" not in metrics  # an embedded database has no network check


def test_starting_a_pipeline_records_it_and_queues_the_first_stage(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, api_runtime: Any
) -> None:
    queued: list[tuple[str, dict[str, object]]] = []

    def fake_enqueue(self: Any, kind: str, payload: dict[str, object]) -> str:
        queued.append((kind, payload))
        return "job-9"

    monkeypatch.setattr(
        "engineering_influence.infrastructure.rabbitmq_queue.RabbitMqQueueAdapter.enqueue",
        fake_enqueue,
    )
    settings = settings_for(tmp_path)
    client = TestClient(api_runtime(settings, Secrets({"EI_API_KEYS": KEY})).build_app())

    response = client.post(
        "/v1/pipelines", json=PROJECT, headers={**AUTH, "X-Request-ID": "client-req-0001"}
    )

    assert response.json() == {"job_id": "job-9", "project_slug": "demo"}
    kind, payload = queued[0]
    assert kind == "pipeline.thesis"
    assert payload["remaining_stages"] == ["book"]
    assert payload["correlation_id"] == "client-req-0001"
    reader = SqlModelLedger(settings.database_url)
    events = reader.events()
    reader.close()
    assert events[0][0] == "pipeline.started"
    assert events[0][1]["remaining_stages"] == ["book"]


def test_the_api_cannot_be_built_without_api_keys(tmp_path: Path, api_runtime: Any) -> None:
    with pytest.raises(ApplicationError, match="EI_API_KEYS"):
        api_runtime(settings_for(tmp_path), Secrets({})).build_app()


def test_the_api_serves_on_the_configured_address_and_leaves_logging_to_the_root(
    tmp_path: Path, process_state: None
) -> None:
    calls: list[tuple[Any, dict[str, Any]]] = []
    settings = settings_for(tmp_path, host="0.0.0.0", port=9001, log_level="WARNING")

    ApiRuntime(
        settings, Secrets({"EI_API_KEYS": KEY}), lambda app, **kw: calls.append((app, kw))
    ).run()

    app, options = calls[0]
    assert options == {"host": "0.0.0.0", "port": 9001, "log_config": None}
    assert TestClient(app).get("/health/live").status_code == 200
    assert logging.getLogger().level == logging.WARNING
    assert ProcessCrashHooks._installed is True


def test_the_default_server_is_uvicorn() -> None:
    assert ApiRuntime._uvicorn() is uvicorn.run


def test_the_worker_builds_a_consumer_and_a_heartbeat(tmp_path: Path) -> None:
    worker = WorkerRuntime(settings_for(tmp_path, queue_name="jobs"))

    consumer, heartbeat = worker.build()
    worker.close()

    assert isinstance(consumer, RabbitMqJobConsumer)
    assert isinstance(heartbeat, WorkerHeartbeat)


def test_closing_twice_is_harmless_and_releases_the_database(tmp_path: Path) -> None:
    worker = WorkerRuntime(settings_for(tmp_path))
    worker.close()  # nothing opened yet
    worker.build()

    worker.close()
    worker.close()

    assert worker._ledger is None


def test_the_api_releases_its_database_when_the_server_stops(
    tmp_path: Path, process_state: None
) -> None:
    runtime = ApiRuntime(
        settings_for(tmp_path), Secrets({"EI_API_KEYS": KEY}), lambda *_a, **_k: None
    )

    runtime.run()

    assert runtime._ledger is None


def test_the_api_releases_its_database_even_when_the_server_crashes(
    tmp_path: Path, process_state: None
) -> None:
    def crashing(*_a: Any, **_k: Any) -> None:
        raise RuntimeError("bind failed")

    runtime = ApiRuntime(settings_for(tmp_path), Secrets({"EI_API_KEYS": KEY}), crashing)

    with pytest.raises(RuntimeError, match="bind failed"):
        runtime.run()

    assert runtime._ledger is None


class FakeHeartbeat:
    def __init__(self) -> None:
        self.events: list[str] = []

    def start(self) -> None:
        self.events.append("start")

    def stop(self) -> None:
        self.events.append("stop")


class FakeConsumer:
    def __init__(self, heartbeat: FakeHeartbeat, fail: bool = False) -> None:
        self._heartbeat = heartbeat
        self._fail = fail

    async def run(self, stop: asyncio.Event) -> None:
        self._heartbeat.events.append("run")
        if self._fail:
            raise ConnectionError("broker gone")
        await stop.wait()


class StubbedWorker(WorkerRuntime):
    def __init__(self, tmp_path: Path, fail: bool = False) -> None:
        super().__init__(settings_for(tmp_path))
        self.heartbeat = FakeHeartbeat()
        self._consumer = FakeConsumer(self.heartbeat, fail)

    def build(self) -> Any:
        return self._consumer, self.heartbeat


def test_the_heartbeat_runs_for_exactly_as_long_as_the_consumer(tmp_path: Path) -> None:
    worker = StubbedWorker(tmp_path)

    async def scenario() -> None:
        stop = asyncio.Event()
        task = asyncio.create_task(worker.serve(stop))
        await asyncio.sleep(0.01)
        stop.set()
        await task

    asyncio.run(scenario())

    assert worker.heartbeat.events == ["start", "run", "stop"]


def test_the_heartbeat_stops_even_when_the_consumer_crashes(tmp_path: Path) -> None:
    worker = StubbedWorker(tmp_path, fail=True)

    with pytest.raises(ConnectionError):
        asyncio.run(worker.serve(asyncio.Event()))

    assert worker.heartbeat.events == ["start", "run", "stop"]


def test_a_real_sigterm_stops_the_worker_cleanly(tmp_path: Path) -> None:
    class SignalledWorker(StubbedWorker):
        async def serve(self, stop: asyncio.Event) -> None:
            os.kill(os.getpid(), signal.SIGTERM)
            await asyncio.wait_for(stop.wait(), timeout=5)
            self.heartbeat.events.append("stopped-by-signal")

    worker = SignalledWorker(tmp_path)

    asyncio.run(worker._main())

    assert worker.heartbeat.events == ["stopped-by-signal"]


def test_running_the_worker_configures_logging_and_crash_hooks(
    tmp_path: Path, process_state: None
) -> None:
    class QuickWorker(StubbedWorker):
        async def _main(self) -> None:
            self.heartbeat.events.append("main")

    worker = QuickWorker(tmp_path)

    worker.run()

    assert worker.heartbeat.events == ["main"]
    assert ProcessCrashHooks._installed is True
    assert any(
        getattr(h, "_engineering_influence_json", False) for h in logging.getLogger().handlers
    )
