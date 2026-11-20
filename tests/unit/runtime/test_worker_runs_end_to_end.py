"""A ``run.advance`` job through the real handler, router, run advancer and SQL stores."""

import asyncio
import json
from typing import Any

from engineering_influence.infrastructure.deterministic_stage_executor import (
    DeterministicStageExecutor,
)
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.job_message_handler import JobMessageHandler
from engineering_influence.infrastructure.observability.context_var_correlation import (
    ContextVarCorrelation,
)
from engineering_influence.interfaces.alert_interface import AlertInterface
from engineering_influence.interfaces.metrics_interface import MetricsInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.repositories.sqlmodel_artifact_store import SqlModelArtifactStore
from engineering_influence.repositories.sqlmodel_journal import SqlModelJournal
from engineering_influence.repositories.sqlmodel_run_repository import SqlModelRunRepository
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.failure_classifier import FailureClassifier
from engineering_influence.services.interfaces.process_job_interface import ProcessJobInterface
from engineering_influence.services.job_router import JobRouter
from engineering_influence.services.process_run_job import ProcessRunJob

STAGES = ("brief", "outline", "draft")


class Delivery:
    def __init__(self, data: bytes) -> None:
        self.body = data
        self.acked = 0
        self.rejected: list[bool] = []

    async def ack(self) -> None:
        self.acked += 1

    async def reject(self, requeue: bool = False) -> None:
        self.rejected.append(requeue)


class Metrics(MetricsInterface):
    def __init__(self) -> None:
        self.seen: dict[str, int] = {}

    def increment(self, name: str, amount: int = 1) -> None:
        self.seen[name] = self.seen.get(name, 0) + amount

    def counters(self) -> dict[str, int]:
        return dict(self.seen)

    def latencies(self) -> dict[str, dict[str, float]]:
        return {}


class Alerts(AlertInterface):
    def __init__(self) -> None:
        self.raised: list[str] = []

    def raise_alert(
        self, severity: str, subject: str, context: dict[str, object], dedup_key: str
    ) -> None:
        self.raised.append(subject)


class Rig:
    """The worker's job path over SQLite, with an in-memory queue standing in for the broker."""

    def __init__(self, database_url: str) -> None:
        self.runs = SqlModelRunRepository(database_url)
        self.journal = SqlModelJournal(database_url)
        self.artifacts = SqlModelArtifactStore(database_url)
        self.queue = InMemoryQueue()
        advance = AdvanceRun(
            self.runs,
            self.journal,
            DeterministicStageExecutor(self.artifacts, self.journal),
            self.queue,
            FailureClassifier(),
        )
        self.metrics, self.alerts = Metrics(), Alerts()
        self.handler = JobMessageHandler(
            JobRouter({"run": ProcessRunJob(advance)}),
            self.metrics,
            self.alerts,
            ContextVarCorrelation(),
        )
        self.deliveries: list[Delivery] = []
        brief = BookBrief(kind=BookKind.NONFICTION, idea="sourdough", budget_micro_usd=1_000)
        plan = StagePlan(kind=BookKind.NONFICTION, stages=STAGES)
        self.runs.save(BookRun("run-1", brief, plan, Budget(cap=1_000)))

    def deliver(self, kind: str, payload: dict[str, Any]) -> Delivery:
        document = {"job_id": f"job-{len(self.deliveries)}", "kind": kind, "payload": payload}
        delivery = Delivery(json.dumps(document).encode())
        self.deliveries.append(delivery)
        asyncio.run(self.handler.handle(delivery))
        return delivery

    def drain(self) -> None:
        while self.queue.jobs:
            kind, payload = self.queue.jobs.pop(0)
            self.deliver(kind, payload)

    def close(self) -> None:
        for store in (self.runs, self.journal, self.artifacts):
            store.close()


def test_a_run_advance_job_runs_every_stage_and_is_acknowledged(database_url: str) -> None:
    rig = Rig(database_url)
    rig.deliver("run.advance", {"run_id": "run-1", "stage": "brief", "attempt": 1})
    rig.drain()

    run = rig.runs.get("run-1")
    assert run is not None
    assert run.status is RunStatus.COMPLETED
    assert rig.artifacts.names("run-1") == ["brief.md", "draft.md", "outline.md"]
    assert rig.artifacts.get("run-1", "outline.md") == b"outline: draft for sourdough"
    assert all(delivery.acked == 1 and delivery.rejected == [] for delivery in rig.deliveries)
    assert rig.metrics.seen["jobs.outcome.run_advanced"] == 2
    assert rig.metrics.seen["jobs.outcome.run_completed"] == 1
    assert rig.alerts.raised == []
    rig.close()


def test_a_redelivered_job_is_acknowledged_and_changes_nothing(database_url: str) -> None:
    rig = Rig(database_url)
    payload = {"run_id": "run-1", "stage": "brief", "attempt": 1}
    rig.deliver("run.advance", payload)
    rig.queue.jobs.clear()
    before = rig.runs.get("run-1")
    delivery = rig.deliver("run.advance", payload)
    assert delivery.acked == 1
    assert rig.runs.get("run-1") == before
    assert [kind for kind, _ in rig.queue.jobs] == ["run.advance"]  # the repair
    assert rig.metrics.seen["jobs.outcome.run_repaired"] == 1
    rig.close()


def test_a_job_for_an_unknown_run_is_dead_lettered_with_an_alert(database_url: str) -> None:
    rig = Rig(database_url)
    delivery = rig.deliver("run.advance", {"run_id": "nope", "stage": "brief", "attempt": 1})
    assert (delivery.acked, delivery.rejected) == (0, [False])
    assert rig.alerts.raised == ["job run.advance failed and was dead-lettered"]
    rig.close()


def test_a_job_kind_the_worker_does_not_handle_is_dead_lettered(database_url: str) -> None:
    rig = Rig(database_url)
    delivery = rig.deliver("other.thing", {"run_id": "run-1"})
    assert (delivery.acked, delivery.rejected) == (0, [False])
    assert rig.metrics.seen["jobs.failed"] == 1
    rig.close()


def test_the_router_is_a_process_job_so_the_handler_does_not_care(database_url: str) -> None:
    assert isinstance(JobRouter({}), ProcessJobInterface)
