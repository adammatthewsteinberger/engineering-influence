"""session/load: a client that reconnects to a new process re-attaches its session and sees where the run stands."""

import pytest

from engineering_influence.infrastructure.in_memory_acp_session_store import InMemoryAcpSessionStore
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interactions.acp.application import AcpApplication
from engineering_influence.models.acp_session import AcpSession
from engineering_influence.models.spend_request import SpendRequest
from engineering_influence.services.brief_reader import BriefReader
from engineering_influence.services.cancel_run import CancelRun
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent
from engineering_influence.services.run_progress import RunProgress

BRIEF_TOML = 'kind = "nonfiction"\nidea = "Windowsill herbs"\nbudget_micro_usd = 1000\n'


def agent(
    repo: InMemoryRunRepository, store: InMemoryAcpSessionStore, queue: InMemoryQueue
) -> AcpApplication:
    """One process: every process of an agent shares the run store and the session store, not memory."""
    return AcpApplication(
        CreateRun(repo, queue, new_id=lambda: "run-1"),
        CancelRun(repo),
        BriefReader(),
        RunProgress(repo),
        ResolveSpendConsent(repo, queue),
        store,
    )


def started() -> tuple[InMemoryRunRepository, InMemoryAcpSessionStore, InMemoryQueue, str]:
    repo, store, queue = InMemoryRunRepository(), InMemoryAcpSessionStore(), InMemoryQueue()
    app = agent(repo, store, queue)
    session_id = app.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "session/new", "params": {"cwd": "/work"}}
    )[0]["result"]["sessionId"]
    app.handle(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "session/prompt",
            "params": {"sessionId": session_id, "prompt": [{"type": "text", "text": BRIEF_TOML}]},
        }
    )
    return repo, store, queue, session_id


def load(app: AcpApplication, session_id: str, cwd: str = "/work") -> list[dict]:
    return app.handle(
        {
            "jsonrpc": "2.0",
            "id": 9,
            "method": "session/load",
            "params": {"sessionId": session_id, "cwd": cwd, "mcpServers": []},
        }
    )


def test_a_new_session_and_its_prompt_are_stored() -> None:
    _, store, _, session_id = started()
    stored = store.get(session_id)
    assert stored == AcpSession(session_id, "/work", "run-1")


def test_a_new_process_loads_the_session_and_replays_where_the_run_stands() -> None:
    repo, store, queue, session_id = started()
    reborn = agent(repo, store, queue)
    messages = load(reborn, session_id)
    assert messages[-1] == {"jsonrpc": "2.0", "id": 9, "result": None}
    assert messages[0]["method"] == "session/update"
    assert "run run-1 is pending" in messages[0]["params"]["update"]["content"]["text"]


def test_after_loading_the_run_is_followed_again() -> None:
    repo, store, queue, session_id = started()
    reborn = agent(repo, store, queue)
    load(reborn, session_id)
    running = repo.get("run-1").start()  # type: ignore[union-attr]
    repo.save(running)
    [notice] = reborn.follow_messages()
    assert "is running" in notice["params"]["update"]["content"]["text"]


def test_a_loaded_run_that_is_waiting_for_consent_is_asked_again_only_on_a_change() -> None:
    repo, store, queue, session_id = started()
    reborn = agent(repo, store, queue)
    waiting = repo.get("run-1").start().await_consent(SpendRequest(700, "brief"))  # type: ignore[union-attr]
    repo.save(waiting)
    load(reborn, session_id)
    assert (
        any(m.get("method") == "session/request_permission" for m in reborn.follow_messages())
        is False
    )


def test_a_finished_run_is_replayed_but_not_followed_after_loading() -> None:
    from engineering_influence.models.book_brief import BookBrief
    from engineering_influence.models.book_kind import BookKind
    from engineering_influence.models.book_run import BookRun
    from engineering_influence.models.budget import Budget
    from engineering_influence.models.stage_plan import StagePlan

    repo, store, queue, session_id = started()
    repo.save(repo.get("run-1").start().fail())  # type: ignore[union-attr]
    reborn = agent(repo, store, queue)
    messages = load(reborn, session_id)
    assert "is failed" in messages[0]["params"]["update"]["content"]["text"]
    # A finished run is not followed, so a different state saved for it later is not reported either.
    brief = BookBrief(BookKind.NONFICTION, "Windowsill herbs", 1_000)
    plan = StagePlan(kind=BookKind.NONFICTION, stages=("brief", "outline"))
    repo.save(BookRun("run-1", brief, plan, Budget(cap=1_000)).start())
    assert reborn.follow_messages() == []


def test_a_session_with_no_run_yet_loads_with_no_replay() -> None:
    repo, store, queue = InMemoryRunRepository(), InMemoryAcpSessionStore(), InMemoryQueue()
    first = agent(repo, store, queue)
    session_id = first.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "session/new", "params": {"cwd": "/work"}}
    )[0]["result"]["sessionId"]
    assert load(agent(repo, store, queue), session_id) == [
        {"jsonrpc": "2.0", "id": 9, "result": None}
    ]


def test_a_run_the_store_no_longer_has_is_not_replayed() -> None:
    _, store, queue, session_id = started()
    reborn = agent(InMemoryRunRepository(), store, queue)
    assert load(reborn, session_id) == [{"jsonrpc": "2.0", "id": 9, "result": None}]


def test_an_unknown_session_is_refused() -> None:
    repo, store, queue, _ = started()
    [reply] = load(agent(repo, store, queue), "sess_never")
    assert reply["error"]["code"] == -32602


def test_loading_needs_an_absolute_working_directory() -> None:
    repo, store, queue, session_id = started()
    [reply] = load(agent(repo, store, queue), session_id, cwd="work")
    assert reply["error"]["code"] == -32602


def test_a_session_that_already_has_a_run_in_this_process_is_not_given_another() -> None:
    repo, store, queue, session_id = started()
    app = agent(repo, store, queue)
    load(app, session_id)
    reply = app.handle(
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "session/prompt",
            "params": {"sessionId": session_id, "prompt": [{"type": "text", "text": BRIEF_TOML}]},
        }
    )
    assert reply[0]["error"]["code"] == -32602


def test_a_session_store_keeps_only_absolute_directories() -> None:
    with pytest.raises(ValueError):
        AcpSession("sess_x", "relative")
    with pytest.raises(ValueError):
        AcpSession(" ", "/work")


@pytest.fixture(params=["memory", "sql"])
def session_store(request: pytest.FixtureRequest, database_url: str) -> object:
    if request.param == "memory":
        return InMemoryAcpSessionStore()
    from engineering_influence.repositories.sqlmodel_acp_session_store import (
        SqlModelAcpSessionStore,
    )

    return SqlModelAcpSessionStore(database_url)


def test_a_session_store_returns_what_was_saved_and_replaces_it(session_store: object) -> None:
    store = session_store  # type: ignore[assignment]
    assert store.get("sess_a") is None  # type: ignore[attr-defined]
    store.save(AcpSession("sess_a", "/work"))  # type: ignore[attr-defined]
    store.save(AcpSession("sess_a", "/elsewhere", "run-1"))  # type: ignore[attr-defined]
    assert store.get("sess_a") == AcpSession("sess_a", "/elsewhere", "run-1")  # type: ignore[attr-defined]
