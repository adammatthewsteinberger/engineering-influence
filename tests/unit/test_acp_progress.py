"""Progress streaming: a session's run is followed, each change is reported once, and a finished run stops being followed."""

import io
import json
import threading
from collections.abc import Iterator

import pytest

from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interactions.acp.application import AcpApplication
from engineering_influence.models.book_run import BookRun
from engineering_influence.services.brief_reader import BriefReader
from engineering_influence.services.cancel_run import CancelRun
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.interfaces.run_progress_interface import RunProgressInterface
from engineering_influence.services.run_progress import RunProgress

BRIEF_TOML = 'kind = "nonfiction"\nidea = "Windowsill herbs"\nbudget_micro_usd = 5000000\n'


class Broken(RunProgressInterface):
    def current(self, run_id: str) -> BookRun | None:
        raise ConnectionError("amqp://ei:hunter2@rabbitmq refused")


def stack(
    repo: InMemoryRunRepository,
    progress: RunProgressInterface | None = None,
) -> AcpApplication:
    return AcpApplication(
        CreateRun(repo, InMemoryQueue(), new_id=lambda: "run-1"),
        CancelRun(repo),
        BriefReader(),
        progress or RunProgress(repo),
    )


def started(app: AcpApplication) -> str:
    """A session whose prompt has started run-1; returns the session id."""
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
    return session_id


def texts(notices: list[dict]) -> list[str]:
    return [notice["params"]["update"]["content"]["text"] for notice in notices]


def says(run: BookRun) -> str:
    return f"run run-1 is {run.status.value} at stage {run.stage!r}"


def test_nothing_is_reported_while_the_run_is_unchanged() -> None:
    repo = InMemoryRunRepository()
    app = stack(repo)
    started(app)
    assert app.progress_notices() == []


def test_a_change_is_reported_once_with_the_session_it_belongs_to() -> None:
    repo = InMemoryRunRepository()
    app = stack(repo)
    session_id = started(app)
    running = repo.get("run-1").start()
    repo.save(running)

    notices = app.progress_notices()
    assert texts(notices) == [says(running)]
    assert notices[0]["method"] == "session/update"
    assert notices[0]["params"]["sessionId"] == session_id
    assert app.progress_notices() == []


def test_a_stage_change_is_reported_as_well_as_a_status_change() -> None:
    repo = InMemoryRunRepository()
    app = stack(repo)
    started(app)
    first = repo.get("run-1").start()
    repo.save(first)
    app.progress_notices()

    advanced = first.advance()
    repo.save(advanced)
    assert texts(app.progress_notices()) == [says(advanced)]


def test_a_parked_run_is_still_followed_and_a_failed_run_is_reported_once_then_dropped() -> None:
    repo = InMemoryRunRepository()
    app = stack(repo)
    started(app)
    parked = repo.get("run-1").start().park()
    repo.save(parked)
    assert texts(app.progress_notices()) == [says(parked)]

    failed = parked.resume().fail()
    repo.save(failed)
    assert texts(app.progress_notices()) == [says(failed)]

    # Dropped: a later saved state is no longer reported.
    repo.save(parked)
    assert app.progress_notices() == []


def test_a_cancelled_run_is_reported_when_the_session_cancels_it() -> None:
    repo = InMemoryRunRepository()
    app = stack(repo)
    session_id = started(app)
    assert (
        app.handle(
            {"jsonrpc": "2.0", "method": "session/cancel", "params": {"sessionId": session_id}}
        )
        == []
    )

    notices = app.progress_notices()
    assert texts(notices) == [says(repo.get("run-1"))]
    assert "cancelled" in texts(notices)[0]


def test_a_run_the_store_does_not_have_is_skipped_and_still_followed() -> None:
    app = stack(InMemoryRunRepository(), progress=RunProgress(InMemoryRunRepository()))
    started(app)
    assert app.progress_notices() == []


def test_serve_writes_a_change_that_happened_before_it_started() -> None:
    repo = InMemoryRunRepository()
    app = stack(repo)
    started(app)
    repo.save(repo.get("run-1").start())

    writer = io.StringIO()
    app.serve(io.StringIO(""), writer, poll_seconds=0.01)
    [line] = writer.getvalue().splitlines()
    assert json.loads(line)["params"]["update"]["content"]["text"] == says(repo.get("run-1"))


def test_every_line_is_one_complete_message_even_with_notices_in_between() -> None:
    repo = InMemoryRunRepository()
    app = stack(repo)
    started(app)
    repo.save(repo.get("run-1").start())

    reader = io.StringIO(
        json.dumps(
            {"jsonrpc": "2.0", "id": 9, "method": "initialize", "params": {"protocolVersion": 1}}
        )
        + "\n"
    )
    writer = io.StringIO()
    app.serve(reader, writer, poll_seconds=0.01)
    messages = [json.loads(line) for line in writer.getvalue().splitlines()]
    assert any(m.get("id") == 9 for m in messages)
    assert any(m.get("method") == "session/update" for m in messages)


def test_a_store_failure_is_one_line_on_stderr_and_the_server_keeps_serving(
    capsys: pytest.CaptureFixture[str],
) -> None:
    app = stack(InMemoryRunRepository(), progress=Broken())
    started(app)
    writer = io.StringIO()
    app.serve(io.StringIO(""), writer, poll_seconds=0.01)
    err = capsys.readouterr().err
    assert err == "error: ConnectionError while following a run\n"
    assert "hunter2" not in err


class FlakyThenRecovered(RunProgressInterface):
    """Fails the first read; from the second, the run has started, and the event says so."""

    def __init__(self, repo: InMemoryRunRepository, recovered: threading.Event) -> None:
        self._repo = repo
        self._recovered = recovered
        self._calls = 0

    def current(self, run_id: str) -> BookRun | None:
        self._calls += 1
        if self._calls == 1:
            raise ConnectionError("amqp://ei:hunter2@rabbitmq refused")
        self._recovered.set()
        stored = self._repo.get(run_id)
        return None if stored is None else stored.start()


class HoldOpenUntil:
    """A reader that stays open until the event is set, then ends."""

    def __init__(self, event: threading.Event) -> None:
        self._event = event

    def __iter__(self) -> Iterator[str]:
        self._event.wait(timeout=5)
        return iter(())


def test_the_follower_keeps_going_after_a_store_failure(
    capsys: pytest.CaptureFixture[str],
) -> None:
    repo = InMemoryRunRepository()
    recovered = threading.Event()
    app = stack(repo, progress=FlakyThenRecovered(repo, recovered))
    started(app)

    writer = io.StringIO()
    app.serve(HoldOpenUntil(recovered), writer, poll_seconds=0.01)  # type: ignore[arg-type]
    notices = [json.loads(line) for line in writer.getvalue().splitlines()]
    assert texts(notices) == [says(repo.get("run-1").start())]
    err = capsys.readouterr().err
    assert err == "error: ConnectionError while following a run\n"
    assert "hunter2" not in err
