"""Service tracing, crash hooks and the worker heartbeat."""

import asyncio
import logging
import sys
import threading
import time
from collections.abc import Iterator
from typing import Any

import pytest
from vibey_bootstrap.tracing.decorators import traced

from engineering_influence.domain.gate import Gate
from engineering_influence.domain.gate_kind import GateKind
from engineering_influence.domain.governing_postulates import GoverningPostulates
from engineering_influence.domain.phase_run import PhaseRun
from engineering_influence.domain.phase_state import PhaseState
from engineering_influence.domain.pipeline_stage import PipelineStage
from engineering_influence.domain.project import Project
from engineering_influence.infrastructure.observability.bootstrap_metrics import BootstrapMetrics
from engineering_influence.infrastructure.observability.process_crash_hooks import (
    ProcessCrashHooks,
)
from engineering_influence.infrastructure.observability.traced_dispatch_outbox import (
    TracedDispatchOutbox,
)
from engineering_influence.infrastructure.observability.traced_run_phase import TracedRunPhase
from engineering_influence.infrastructure.observability.traced_start_pipeline import (
    TracedStartPipeline,
)
from engineering_influence.infrastructure.observability.worker_heartbeat import WorkerHeartbeat
from engineering_influence.interfaces.alert_port import AlertPort
from engineering_influence.interfaces.metrics_port import MetricsPort
from engineering_influence.services.interfaces.dispatch_outbox_interface import (
    DispatchOutboxInterface,
)
from engineering_influence.services.interfaces.run_phase_interface import RunPhaseInterface
from engineering_influence.services.interfaces.start_pipeline_interface import (
    StartPipelineInterface,
)

PROJECT = Project("demo", "Demo", GoverningPostulates(("Evidence.",)), (PipelineStage.THESIS,))
MANUSCRIPT = "THE-CHAPTER-TEXT-THAT-MUST-NOT-BE-LOGGED"
SECRET = b"webhook-signing-secret-bytes"


class Starter(StartPipelineInterface):
    def __init__(self, fail: bool = False) -> None:
        self._fail = fail

    def start(self, project: Project) -> str:
        if self._fail:
            raise RuntimeError("start failed")
        return "job-1"


class Runner(RunPhaseInterface):
    async def run(
        self, phase_run: PhaseRun, artifact_type: str, gate: Gate, context: dict[str, object]
    ) -> Any:
        return phase_run, artifact_type


class Dispatcher(DispatchOutboxInterface):
    async def dispatch(self, secret: bytes) -> int:
        return 3


@pytest.fixture
def debug_log(caplog: pytest.LogCaptureFixture) -> pytest.LogCaptureFixture:
    caplog.set_level(logging.DEBUG)
    return caplog


def latency_for(operation: str) -> dict[str, float]:
    return BootstrapMetrics().latencies()[operation]


def test_traced_start_delegates_and_records_latency(debug_log: pytest.LogCaptureFixture) -> None:
    before = BootstrapMetrics().latencies().get("service.start_pipeline", {}).get("count", 0)

    assert TracedStartPipeline(Starter()).start(PROJECT) == "job-1"

    assert latency_for("service.start_pipeline")["count"] == before + 1


def test_traced_start_records_errors_and_still_raises() -> None:
    before = BootstrapMetrics().latencies().get("service.start_pipeline", {}).get("errors", 0)

    with pytest.raises(RuntimeError, match="start failed"):
        TracedStartPipeline(Starter(fail=True)).start(PROJECT)

    assert latency_for("service.start_pipeline")["errors"] == before + 1


def call_args_logged(caplog: pytest.LogCaptureFixture, operation: str) -> dict[str, str]:
    """Return the argument summary of the entry record for an operation."""
    for record in caplog.records:
        if getattr(record, "operation", None) == operation and hasattr(record, "call_args"):
            return dict(record.call_args)
    raise AssertionError(f"no entry record for {operation}")


def everything_logged(caplog: pytest.LogCaptureFixture) -> str:
    """Every attribute of every record, including the extras a text formatter hides."""
    return " ".join(str(vars(record)) for record in caplog.records)


def test_an_unmasked_string_argument_would_be_logged_verbatim(
    debug_log: pytest.LogCaptureFixture,
) -> None:
    @traced(operation="control.unmasked")
    def leaky(text: str) -> int:
        return len(text)

    leaky(MANUSCRIPT)

    assert MANUSCRIPT in everything_logged(debug_log)


def test_start_masks_the_project(debug_log: pytest.LogCaptureFixture) -> None:
    TracedStartPipeline(Starter()).start(PROJECT)

    assert call_args_logged(debug_log, "service.start_pipeline") == {"project": "***"}


def test_run_phase_masks_every_argument_including_the_manuscript_context(
    debug_log: pytest.LogCaptureFixture,
) -> None:
    phase = PhaseRun("run-1", "thesis.p1", PhaseState.QUEUED)
    gate = Gate("thesis", GateKind.AUTO, "rubric")

    result = asyncio.run(TracedRunPhase(Runner()).run(phase, "thesis", gate, {"draft": MANUSCRIPT}))

    assert result == (phase, "thesis")
    assert call_args_logged(debug_log, "service.run_phase") == {
        "phase_run": "***",
        "artifact_type": "***",
        "gate": "***",
        "context": "***",
    }
    assert MANUSCRIPT not in everything_logged(debug_log)


def test_dispatch_masks_the_signing_secret(debug_log: pytest.LogCaptureFixture) -> None:
    assert asyncio.run(TracedDispatchOutbox(Dispatcher()).dispatch(SECRET)) == 3

    assert call_args_logged(debug_log, "service.dispatch_outbox") == {"secret": "***"}
    assert SECRET.decode() not in everything_logged(debug_log)


@pytest.fixture
def restore_hooks() -> Iterator[None]:
    saved_hook, saved_flag = sys.excepthook, ProcessCrashHooks._installed
    ProcessCrashHooks._installed = False
    yield
    sys.excepthook = saved_hook
    ProcessCrashHooks._installed = saved_flag


def test_crash_hooks_install_once(restore_hooks: None) -> None:
    hooks = ProcessCrashHooks()
    original = sys.excepthook

    assert hooks.install() is True
    installed = sys.excepthook
    assert installed is not original
    assert hooks.install() is False
    assert ProcessCrashHooks().install() is False
    assert sys.excepthook is installed


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class RecordingAlerts(AlertPort):
    def __init__(self) -> None:
        self.raised: list[tuple[str, str, dict[str, object], str]] = []

    def raise_alert(
        self, severity: str, subject: str, context: dict[str, object], dedup_key: str
    ) -> None:
        self.raised.append((severity, subject, context, dedup_key))


class StubMetrics(MetricsPort):
    def increment(self, name: str, amount: int = 1) -> None:
        return None

    def counters(self) -> dict[str, int]:
        return {"jobs": 4}

    def latencies(self) -> dict[str, dict[str, float]]:
        return {"op": {"p95": 0.5}}


def heartbeat(clock: FakeClock, alerts: RecordingAlerts, **overrides: float) -> WorkerHeartbeat:
    settings = {"silence_seconds": 100.0, "realert_seconds": 500.0, **overrides}
    return WorkerHeartbeat(StubMetrics(), alerts, clock=clock, **settings)


def test_a_worker_making_progress_is_never_alerted() -> None:
    clock, alerts = FakeClock(), RecordingAlerts()
    worker = heartbeat(clock, alerts)

    for _ in range(5):
        clock.now += 90
        worker.record_progress()
        assert worker.check_silence() is False

    assert alerts.raised == []


def test_a_silent_worker_raises_a_critical_alert() -> None:
    clock, alerts = FakeClock(), RecordingAlerts()
    worker = heartbeat(clock, alerts)
    clock.now += 101

    assert worker.check_silence() is True

    severity, subject, context, dedup_key = alerts.raised[0]
    assert (severity, subject, dedup_key) == (
        "critical",
        "worker is not making progress",
        "worker:silent",
    )
    assert context == {"silent_seconds": 101, "threshold_seconds": 100}


def test_a_worker_that_never_made_progress_is_still_caught() -> None:
    clock, alerts = FakeClock(), RecordingAlerts()
    worker = heartbeat(clock, alerts)  # constructed, then nothing is ever handled
    clock.now += 10_000

    assert worker.check_silence() is True


def test_a_sustained_stall_is_realerted_only_after_the_window() -> None:
    clock, alerts = FakeClock(), RecordingAlerts()
    worker = heartbeat(clock, alerts)
    clock.now += 101
    worker.check_silence()
    clock.now += 400
    assert worker.check_silence() is False
    clock.now += 101
    assert worker.check_silence() is True

    assert len(alerts.raised) == 2


def test_recovery_then_a_new_stall_alerts_again_after_the_window() -> None:
    clock, alerts = FakeClock(), RecordingAlerts()
    worker = heartbeat(clock, alerts, realert_seconds=50.0)
    clock.now += 101
    worker.check_silence()
    worker.record_progress()
    clock.now += 101

    assert worker.check_silence() is True


@pytest.mark.parametrize(
    "setting", ["heartbeat_seconds", "silence_seconds", "check_seconds", "realert_seconds"]
)
def test_every_interval_must_be_positive(setting: str) -> None:
    with pytest.raises(ValueError, match="positive"):
        WorkerHeartbeat(StubMetrics(), RecordingAlerts(), **{setting: 0})  # type: ignore[arg-type]


def test_the_threads_run_the_watchdog_and_stop_cleanly() -> None:
    alerts = RecordingAlerts()
    worker = WorkerHeartbeat(
        StubMetrics(), alerts, heartbeat_seconds=0.05, silence_seconds=0.05, check_seconds=0.02
    )
    worker.start()
    deadline = time.monotonic() + 3
    while not alerts.raised and time.monotonic() < deadline:
        time.sleep(0.02)
    worker.stop()

    assert alerts.raised and alerts.raised[0][3] == "worker:silent"
    assert not any(t.name == "worker-watchdog" and t.is_alive() for t in threading.enumerate())


def test_starting_twice_is_an_error_and_stop_allows_a_restart() -> None:
    worker = WorkerHeartbeat(
        StubMetrics(), RecordingAlerts(), heartbeat_seconds=60, check_seconds=60
    )
    worker.start()
    with pytest.raises(RuntimeError, match="already started"):
        worker.start()
    worker.stop()
    worker.start()
    worker.stop()


def test_the_heartbeat_snapshot_uses_the_metrics_port() -> None:
    worker = WorkerHeartbeat(StubMetrics(), RecordingAlerts())

    assert worker._snapshot() == {"counters": {"jobs": 4}, "latency_snapshot": {"op": {"p95": 0.5}}}
