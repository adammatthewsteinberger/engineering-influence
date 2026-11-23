"""The Agent Client Protocol: sessions start runs, prompts are briefs, and refusals are JSON-RPC errors."""

import io
import json
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interactions.acp.application import AcpApplication
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.stage_plan import StagePlan
from engineering_influence.services.brief_reader import BriefReader
from engineering_influence.services.cancel_run import CancelRun
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.interfaces.cancel_run_interface import CancelRunInterface
from engineering_influence.services.interfaces.create_run_interface import CreateRunInterface

BRIEF_TOML = 'kind = "nonfiction"\nidea = "Windowsill herbs"\nbudget_micro_usd = 5000000\n'


class Creator(CreateRunInterface):
    def __init__(self, failure: BaseException | None = None) -> None:
        self.failure = failure
        self.briefs: list[BookBrief] = []

    def create(self, brief: BookBrief) -> BookRun:
        if self.failure is not None:
            raise self.failure
        self.briefs.append(brief)
        plan = StagePlan(kind=brief.kind, stages=("brief", "outline"))
        return BookRun("run-1", brief, plan, Budget(cap=brief.budget_micro_usd))


class Canceller(CancelRunInterface):
    def __init__(self) -> None:
        self.seen: list[str] = []

    def cancel(self, run_id: str) -> BookRun:
        self.seen.append(run_id)
        brief = BookBrief(BookKind.NONFICTION, "Windowsill herbs", 5_000_000)
        plan = StagePlan(kind=BookKind.NONFICTION, stages=("brief", "outline"))
        return BookRun(run_id, brief, plan, Budget(cap=5_000_000), status=RunStatus.CANCELLED)


class FailingCanceller(CancelRunInterface):
    def cancel(self, run_id: str) -> BookRun:
        raise RuntimeError(f"cannot stop {run_id}")


def app(
    creator: CreateRunInterface | None = None,
    canceller: CancelRunInterface | None = None,
) -> AcpApplication:
    return AcpApplication(creator or Creator(), canceller or Canceller(), BriefReader())


def request(method: str, request_id: int = 1, **params: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}


def new_session(agent: AcpApplication) -> str:
    reply = agent.handle(request("session/new", cwd="/work/book"))
    return reply[0]["result"]["sessionId"]


def prompt(text: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": text}]


def test_initialize_agrees_protocol_version_one() -> None:
    reply = app().handle(request("initialize", protocolVersion=1))
    assert reply[0]["id"] == 1
    result = reply[0]["result"]
    assert result["protocolVersion"] == 1
    assert result["agentInfo"]["name"] == "engineering-influence"
    assert result["authMethods"] == []
    assert result["agentCapabilities"] == {"loadSession": False}


def test_session_new_returns_a_session_id() -> None:
    agent = app()
    session_id = new_session(agent)
    assert session_id.startswith("sess_")
    assert len(session_id) == len("sess_") + 32


def test_session_new_refuses_a_relative_cwd() -> None:
    reply = app().handle(request("session/new", cwd="book"))
    assert reply[0]["error"]["code"] == -32602
    assert "absolute path" in reply[0]["error"]["message"]


def test_session_new_refuses_mcp_servers_it_does_not_connect() -> None:
    reply = app().handle(request("session/new", cwd="/work", mcpServers=[{"name": "fs"}]))
    assert reply[0]["error"]["code"] == -32602
    assert "MCP" in reply[0]["error"]["message"]


def test_prompt_starts_a_run_and_ends_the_turn() -> None:
    creator = Creator()
    agent = app(creator)
    session_id = new_session(agent)
    reply = agent.handle(
        request("session/prompt", 2, sessionId=session_id, prompt=prompt(BRIEF_TOML))
    )
    notice, answer = reply
    assert notice["method"] == "session/update"
    assert notice["params"]["sessionId"] == session_id
    assert notice["params"]["update"]["sessionUpdate"] == "agent_message_chunk"
    assert notice["params"]["update"]["content"]["text"].startswith("run run-1 is ")
    assert answer == {"jsonrpc": "2.0", "id": 2, "result": {"stopReason": "end_turn"}}
    [brief] = creator.briefs
    assert (brief.kind, brief.idea, brief.budget_micro_usd) == (
        BookKind.NONFICTION,
        "Windowsill herbs",
        5_000_000,
    )


def test_a_prompt_is_read_the_same_way_as_a_brief_file_would_be() -> None:
    """ACP and ``ei run create`` store the same run, because both read the brief with BriefReader and create it with CreateRun."""
    from_file = BriefReader().read_text(BRIEF_TOML, "brief.toml")
    direct = CreateRun(InMemoryRunRepository(), InMemoryQueue(), new_id=lambda: "run-1").create(
        from_file
    )

    acp_repository = InMemoryRunRepository()
    agent = AcpApplication(
        CreateRun(acp_repository, InMemoryQueue(), new_id=lambda: "run-1"),
        CancelRun(acp_repository),
        BriefReader(),
    )
    session_id = new_session(agent)
    agent.handle(request("session/prompt", sessionId=session_id, prompt=prompt(BRIEF_TOML)))

    stored = acp_repository.get("run-1")
    assert stored is not None
    assert stored.brief == direct.brief
    assert stored.status == direct.status
    assert stored.stage == direct.stage


def test_the_prompt_text_joins_its_text_blocks_in_order() -> None:
    creator = Creator()
    agent = app(creator)
    session_id = new_session(agent)
    # Neither block ends in a newline, so only a newline between them makes valid TOML.
    blocks = [
        {"type": "text", "text": 'kind = "nonfiction"\nidea = "Herbs"'},
        {"type": "text", "text": "budget_micro_usd = 1000"},
    ]
    agent.handle(request("session/prompt", sessionId=session_id, prompt=blocks))
    [brief] = creator.briefs
    assert (brief.idea, brief.budget_micro_usd) == ("Herbs", 1000)


def test_a_second_prompt_in_the_same_session_is_refused() -> None:
    agent = app()
    session_id = new_session(agent)
    agent.handle(request("session/prompt", sessionId=session_id, prompt=prompt(BRIEF_TOML)))
    reply = agent.handle(
        request("session/prompt", 3, sessionId=session_id, prompt=prompt(BRIEF_TOML))
    )
    assert reply[0]["error"]["code"] == -32602
    assert "already has run run-1" in reply[0]["error"]["message"]


def test_a_prompt_for_an_unknown_session_is_refused() -> None:
    reply = app().handle(
        request("session/prompt", sessionId="sess_nope", prompt=prompt(BRIEF_TOML))
    )
    assert reply[0]["error"]["code"] == -32602
    assert "names a session this agent started" in reply[0]["error"]["message"]


def test_a_prompt_must_be_a_non_empty_list_of_text_blocks() -> None:
    agent = app()
    session_id = new_session(agent)
    empty = agent.handle(request("session/prompt", sessionId=session_id, prompt=[]))
    image = agent.handle(
        request("session/prompt", sessionId=session_id, prompt=[{"type": "image", "data": "x"}])
    )
    assert empty[0]["error"]["code"] == -32602
    assert image[0]["error"]["code"] == -32602
    assert "text content blocks" in image[0]["error"]["message"]


def test_a_prompt_that_is_not_toml_is_refused_and_names_the_prompt() -> None:
    agent = app()
    session_id = new_session(agent)
    reply = agent.handle(request("session/prompt", sessionId=session_id, prompt=prompt("kind = ")))
    assert reply[0]["error"]["code"] == -32602
    assert reply[0]["error"]["message"].startswith("the prompt is not valid TOML")


def test_a_prompt_that_is_not_a_brief_is_refused() -> None:
    agent = app()
    session_id = new_session(agent)
    reply = agent.handle(
        request("session/prompt", sessionId=session_id, prompt=prompt("hello = 1\n"))
    )
    assert reply[0]["error"]["code"] == -32602
    assert reply[0]["error"]["message"].startswith("the prompt is not a brief")


def test_an_unexpected_failure_is_a_generic_internal_error_that_keeps_the_server_up(
    capsys: pytest.CaptureFixture[str],
) -> None:
    agent = app(Creator(failure=ConnectionError("amqp://ei:hunter2@rabbitmq refused")))
    session_id = new_session(agent)
    reply = agent.handle(request("session/prompt", sessionId=session_id, prompt=prompt(BRIEF_TOML)))
    assert reply == [
        {"jsonrpc": "2.0", "id": 1, "error": {"code": -32603, "message": "internal error"}}
    ]
    err = capsys.readouterr().err
    assert "ConnectionError" in err
    assert "hunter2" not in err
    assert "hunter2" not in json.dumps(reply)


def test_an_unexpected_failure_in_a_notification_is_silent_on_the_wire() -> None:
    agent = app(canceller=FailingCanceller())
    session_id = new_session(agent)
    agent.handle(request("session/prompt", sessionId=session_id, prompt=prompt(BRIEF_TOML)))
    assert (
        agent.handle(
            {"jsonrpc": "2.0", "method": "session/cancel", "params": {"sessionId": session_id}}
        )
        == []
    )


def test_a_domain_error_without_an_acp_code_is_an_internal_error() -> None:
    agent = app(
        Creator(failure=ApplicationError(code="RUN_STORE_FULL", message="no room", http_status=507))
    )
    session_id = new_session(agent)
    reply = agent.handle(request("session/prompt", sessionId=session_id, prompt=prompt(BRIEF_TOML)))
    assert reply == [{"jsonrpc": "2.0", "id": 1, "error": {"code": -32603, "message": "no room"}}]


def test_session_cancel_stops_the_session_run() -> None:
    canceller = Canceller()
    agent = app(canceller=canceller)
    session_id = new_session(agent)
    agent.handle(request("session/prompt", sessionId=session_id, prompt=prompt(BRIEF_TOML)))
    assert (
        agent.handle(
            {"jsonrpc": "2.0", "method": "session/cancel", "params": {"sessionId": session_id}}
        )
        == []
    )
    assert canceller.seen == ["run-1"]


def test_session_cancel_before_a_prompt_does_nothing() -> None:
    canceller = Canceller()
    agent = app(canceller=canceller)
    session_id = new_session(agent)
    agent.handle(
        {"jsonrpc": "2.0", "method": "session/cancel", "params": {"sessionId": session_id}}
    )
    assert canceller.seen == []


def test_a_notification_that_fails_gets_no_reply() -> None:
    agent = app()
    assert (
        agent.handle(
            {"jsonrpc": "2.0", "method": "session/cancel", "params": {"sessionId": "sess_nope"}}
        )
        == []
    )


def test_an_unknown_method_is_method_not_found() -> None:
    reply = app().handle(request("session/load", sessionId="sess_1"))
    assert reply[0]["error"] == {
        "code": -32601,
        "message": "this agent does not implement session/load",
    }


def test_a_message_without_the_jsonrpc_version_is_an_invalid_request() -> None:
    reply = app().handle({"id": 4, "method": "initialize"})
    assert reply[0]["error"]["code"] == -32600
    assert reply[0]["id"] == 4


def test_params_that_are_not_an_object_are_invalid() -> None:
    reply = app().handle({"jsonrpc": "2.0", "id": 5, "method": "initialize", "params": [1]})
    assert reply[0]["error"]["code"] == -32602


def test_serve_answers_each_line_and_skips_blank_ones() -> None:
    lines = [
        json.dumps(request("initialize", protocolVersion=1)),
        "",
        "not json",
        json.dumps(request("session/new", cwd="/work")),
    ]
    reader = io.StringIO("\n".join(lines) + "\n")
    writer = io.StringIO()
    app().serve(reader, writer)
    replies = [json.loads(line) for line in writer.getvalue().splitlines()]
    assert len(replies) == 3
    assert replies[0]["result"]["protocolVersion"] == 1
    assert replies[1] == {
        "jsonrpc": "2.0",
        "id": None,
        "error": {"code": -32700, "message": "the line is not JSON"},
    }
    assert replies[2]["result"]["sessionId"].startswith("sess_")
