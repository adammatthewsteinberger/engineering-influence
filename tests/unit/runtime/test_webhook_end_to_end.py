# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The webhook path end to end, with fakes at the network edge: a run queues its events, the dispatcher delivers them,
a failing receiver is retried and then dead-lettered, the signature verifies, and no receiver means no outbox writes."""

import asyncio
import json

import httpx

from engineering_influence.contracts.security_verdict import SecurityVerdict
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.observability.bootstrap_alert_dispatcher import (
    BootstrapAlertDispatcher,
)
from engineering_influence.infrastructure.observability.bootstrap_metrics import BootstrapMetrics
from engineering_influence.infrastructure.observability.worker_heartbeat import WorkerHeartbeat
from engineering_influence.infrastructure.webhooks.delivery import WebhookDelivery
from engineering_influence.infrastructure.webhooks.signer import WebhookSigner
from engineering_influence.interactions.webhooks.signed_request_verifier import (
    SignedRequestVerifier,
)
from engineering_influence.interfaces.outbound_url_policy_interface import (
    OutboundUrlPolicyInterface,
)
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.stage_report import StageReport
from engineering_influence.repositories.sqlmodel_journal import SqlModelJournal
from engineering_influence.repositories.sqlmodel_outbox import SqlModelOutbox
from engineering_influence.repositories.sqlmodel_run_repository import SqlModelRunRepository
from engineering_influence.runtime.app_settings import AppSettings
from engineering_influence.runtime.worker_runtime import WorkerRuntime
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.dispatch_outbox import DispatchOutbox
from engineering_influence.services.failure_classifier import FailureClassifier
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.run_event_builder import RunEventBuilder

URL = "https://hook.example/in"
SECRET = b"receiver-secret"


class Succeeds(StageExecutorInterface):
    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        return StageReport()


class AcceptAll(OutboundUrlPolicyInterface):
    def check(self, url: str) -> SecurityVerdict:
        return SecurityVerdict.accept()


class Receiver:
    """A receiver that answers with the status it is given, and keeps what it was sent."""

    def __init__(self, status: int) -> None:
        self.status = status
        self.requests: list[httpx.Request] = []

    async def deliver(
        self, url: str, event_name: str, event_id: str, payload: dict[str, object], secret: bytes
    ) -> int:
        self.requests.append(httpx.Request("POST", url))
        return self.status


def a_run() -> BookRun:
    brief = BookBrief(BookKind.NONFICTION, "bees", 5_000_000)
    return BookRun(
        run_id="run-1", brief=brief, plan=NonfictionRecipes().plan(), budget=Budget(cap=5_000_000)
    )


def queue_events(database_url: str, urls: tuple[str, ...]) -> None:
    """The first stage of a run, advanced in full: the start and the finished stage are queued in the outbox."""
    runs = SqlModelRunRepository(database_url)
    runs.save(a_run())
    advance = AdvanceRun(
        runs,
        SqlModelJournal(database_url),
        Succeeds(),
        InMemoryQueue(),
        FailureClassifier(),
        events=RunEventBuilder(urls),
    )
    import asyncio

    asyncio.run(advance.advance("run-1", "brief", 1))
    runs.close()


def test_a_run_event_is_delivered_and_marked_delivered(database_url: str) -> None:
    import asyncio

    queue_events(database_url, (URL,))
    outbox = SqlModelOutbox(database_url)
    assert sorted(record[2] for record in outbox.pending()) == [
        "phase.completed",
        "pipeline.started",
    ]
    receiver = Receiver(status=200)
    dispatch = DispatchOutbox(outbox, receiver, BootstrapMetrics(), BootstrapAlertDispatcher())
    assert asyncio.run(dispatch.dispatch(SECRET)) == 2
    assert outbox.pending() == []


def test_a_failing_receiver_is_retried_then_dead_lettered(database_url: str) -> None:
    import asyncio

    queue_events(database_url, (URL,))
    outbox = SqlModelOutbox(database_url)
    dispatch = DispatchOutbox(
        outbox, Receiver(status=500), BootstrapMetrics(), BootstrapAlertDispatcher(), max_attempts=2
    )
    asyncio.run(dispatch.dispatch(SECRET))
    assert len(outbox.pending()) == 2
    asyncio.run(dispatch.dispatch(SECRET))
    assert outbox.pending() == []


def test_the_signed_header_verifies_with_the_existing_verifier(database_url: str) -> None:
    import asyncio

    sent: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200)

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    delivery = WebhookDelivery(client, AcceptAll(), clock=lambda: 1_700_000_000.0)
    status = asyncio.run(
        delivery.deliver(URL, "pipeline.started", "evt-1", {"project_slug": "run-1"}, SECRET)
    )
    assert status == 200
    request = sent[0]
    verifier = SignedRequestVerifier(WebhookSigner(SECRET), clock=lambda: 1_700_000_000.0)
    verdict = verifier.verify(
        request.content,
        request.headers["X-Engineering-Influence-Signature"],
        request.headers["X-Engineering-Influence-Timestamp"],
    )
    assert verdict.accepted is True
    assert json.loads(request.content)["type"] == "pipeline.started"
    asyncio.run(client.aclose())


def test_with_no_receiver_no_outbox_write_happens(database_url: str) -> None:
    queue_events(database_url, ())
    assert SqlModelOutbox(database_url).pending() == []


def test_the_worker_has_no_dispatch_loop_without_a_receiver(database_url: str) -> None:
    settings = AppSettings(database_url=database_url, rabbitmq_url="amqp://unused")
    worker = WorkerRuntime(settings)
    assert worker.webhook_dispatch(BootstrapMetrics(), BootstrapAlertDispatcher()) is None


def test_the_worker_builds_a_dispatch_loop_with_a_receiver(database_url: str) -> None:
    settings = AppSettings(
        database_url=database_url,
        rabbitmq_url="amqp://unused",
        webhook_urls=(URL,),
        webhook_secret="receiver-secret",
        webhook_interval_seconds=1.0,
    )
    worker = WorkerRuntime(settings)
    loop = worker.webhook_dispatch(BootstrapMetrics(), BootstrapAlertDispatcher())
    assert loop is not None


class StoppingConsumer:
    """Runs for a moment, then asks the worker to stop, as a real consumer does on a stop signal."""

    async def run(self, stop: asyncio.Event) -> None:
        await asyncio.sleep(0.02)
        stop.set()


def test_the_dispatch_loop_runs_beside_the_consumer_and_stops_with_it(database_url: str) -> None:
    settings = AppSettings(
        database_url=database_url,
        rabbitmq_url="amqp://unused",
        webhook_urls=(URL,),
        webhook_secret="receiver-secret",
        webhook_interval_seconds=0.01,
    )
    worker = WorkerRuntime(settings)
    metrics, alerts = BootstrapMetrics(), BootstrapAlertDispatcher()
    loop = worker.webhook_dispatch(metrics, alerts)
    heartbeat = WorkerHeartbeat(metrics, alerts)
    stop = asyncio.Event()
    asyncio.run(worker.gather(StoppingConsumer(), heartbeat, loop, stop))  # type: ignore[arg-type]
    assert stop.is_set()


def test_without_a_receiver_only_the_consumer_runs(database_url: str) -> None:
    worker = WorkerRuntime(AppSettings(database_url=database_url, rabbitmq_url="amqp://unused"))
    stop = asyncio.Event()
    heartbeat = WorkerHeartbeat(BootstrapMetrics(), BootstrapAlertDispatcher())
    asyncio.run(worker.gather(StoppingConsumer(), heartbeat, None, stop))  # type: ignore[arg-type]
    assert stop.is_set()
