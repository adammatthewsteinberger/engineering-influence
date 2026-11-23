"""Spend consent over ACP: a run that waits for more budget asks the client, and the answer decides it."""

import io
import json

import pytest

from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interactions.acp.application import AcpApplication
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.spend_request import SpendRequest
from engineering_influence.services.brief_reader import BriefReader
from engineering_influence.services.cancel_run import CancelRun
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent
from engineering_influence.services.run_progress import RunProgress

BRIEF_TOML = 'kind = "nonfiction"\nidea = "Windowsill herbs"\nbudget_micro_usd = 1000\n'


def stack() -> tuple[AcpApplication, InMemoryRunRepository, InMemoryQueue, str]:
    repo, queue = InMemoryRunRepository(), InMemoryQueue()
    app = AcpApplication(
        CreateRun(repo, queue, new_id=lambda: "run-1"),
        CancelRun(repo),
        BriefReader(),
        RunProgress(repo),
        ResolveSpendConsent(repo, queue),
    )
    created = app.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "session/new", "params": {"cwd": "/work"}}
    )
    session_id = created[0]["result"]["sessionId"]
    app.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "session/prompt",
            "params": {"sessionId": session_id, "prompt": [{"type": "text", "text": BRIEF_TOML}]},
        }
    )
    return app, repo, queue, session_id


def ask_for_more(repo: InMemoryRunRepository, requested: int = 700) -> None:
    """The worker parks a run for consent; here the store records the same state directly."""
    run = repo.get("run-1")
    assert run is not None
    repo.save(run.start().await_consent(SpendRequest(requested, "brief")))


def answer(app: AcpApplication, request_id: str, option: str) -> list[dict]:
    return app.handle(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"outcome": {"outcome": "selected", "optionId": option}},
        }
    )


def request_of(messages: list[dict]) -> dict:
    [request] = [m for m in messages if m.get("method") == "session/request_permission"]
    return request


def test_a_run_that_waits_for_consent_asks_the_client_once() -> None:
    app, repo, _, session_id = stack()
    ask_for_more(repo, 700)
    messages = app.follow_messages()
    request = request_of(messages)
    assert request["id"].startswith("consent-")
    assert request["params"]["sessionId"] == session_id
    options = {option["optionId"]: option for option in request["params"]["options"]}
    assert set(options) == {"grant", "deny"}
    assert "700 micro-USD" in options["grant"]["name"]
    assert app.follow_messages() == []


def test_granting_the_request_raises_the_cap_and_queues_the_run() -> None:
    app, repo, queue, _ = stack()
    ask_for_more(repo, 700)
    request_id = request_of(app.follow_messages())["id"]
    assert answer(app, request_id, "grant") == []
    granted = repo.get("run-1")
    assert granted is not None
    assert granted.status is RunStatus.RUNNING
    assert granted.budget.cap == 1_700
    assert queue.jobs[-1][1]["stage"] == "brief"


def test_denying_the_request_parks_the_run_and_queues_nothing() -> None:
    app, repo, queue, _ = stack()
    ask_for_more(repo)
    request_id = request_of(app.follow_messages())["id"]
    jobs_before = len(queue.jobs)
    answer(app, request_id, "deny")
    parked = repo.get("run-1")
    assert parked is not None and parked.status is RunStatus.PARKED_CAPACITY
    assert len(queue.jobs) == jobs_before


def test_an_answer_is_acted_on_once(capsys: pytest.CaptureFixture[str]) -> None:
    app, repo, queue, _ = stack()
    ask_for_more(repo)
    request_id = request_of(app.follow_messages())["id"]
    answer(app, request_id, "grant")
    jobs = len(queue.jobs)
    capsys.readouterr()
    assert answer(app, request_id, "grant") == []
    assert len(queue.jobs) == jobs
    # A second answer is silently ignored; it is not a refused grant of a run that has moved on.
    assert capsys.readouterr().err == ""


def test_a_cancelled_or_unselected_answer_leaves_the_run_waiting(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app, repo, _, _ = stack()
    ask_for_more(repo)
    request_id = request_of(app.follow_messages())["id"]
    app.handle(
        {"jsonrpc": "2.0", "id": request_id, "result": {"outcome": {"outcome": "cancelled"}}}
    )
    app.handle(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {"outcome": {"outcome": "selected", "optionId": "maybe"}},
        }
    )
    app.handle({"jsonrpc": "2.0", "id": request_id, "error": {"code": -1, "message": "no"}})
    waiting = repo.get("run-1")
    assert waiting is not None and waiting.status is RunStatus.AWAITING_CONSENT
    # The request stays open, so a later selected answer still counts.
    answer(app, request_id, "grant")
    running = repo.get("run-1")
    assert running is not None and running.status is RunStatus.RUNNING


def test_an_answer_to_a_run_that_has_moved_on_is_reported_on_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app, repo, _, _ = stack()
    ask_for_more(repo)
    request_id = request_of(app.follow_messages())["id"]
    current = repo.get("run-1")
    assert current is not None
    repo.save(current.cancel())
    assert answer(app, request_id, "grant") == []
    assert (
        capsys.readouterr().err == "error: CONSENT_NOT_PENDING while answering a consent request\n"
    )


def test_an_answer_to_an_unknown_request_is_ignored() -> None:
    app, _, _, _ = stack()
    assert answer(app, "consent-never-sent", "grant") == []


def test_a_run_that_waits_again_after_a_denial_asks_again() -> None:
    app, repo, _, _ = stack()
    ask_for_more(repo, 700)
    answer(app, request_of(app.follow_messages())["id"], "deny")
    app.follow_messages()
    parked = repo.get("run-1")
    assert parked is not None
    repo.save(parked.resume().await_consent(SpendRequest(900, "brief")))
    second = request_of(app.follow_messages())
    assert "900 micro-USD" in second["params"]["options"][0]["name"]


def test_serve_writes_the_request_as_one_complete_line() -> None:
    app, repo, _, _ = stack()
    ask_for_more(repo)
    writer = io.StringIO()
    app.serve(io.StringIO(""), writer, poll_seconds=0.01)
    lines = [json.loads(line) for line in writer.getvalue().splitlines()]
    assert any(line.get("method") == "session/request_permission" for line in lines)
