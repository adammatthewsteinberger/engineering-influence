# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""McpServerProbe: ask a server who it is, always stop it, and never start one whose files changed."""

from collections.abc import Mapping
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.file_hasher_interface import FileHasherInterface
from engineering_influence.interfaces.mcp_remote_transport_factory_interface import (
    McpRemoteTransportFactoryInterface,
)
from engineering_influence.interfaces.mcp_transport_factory_interface import (
    McpTransportFactoryInterface,
)
from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface
from engineering_influence.models.mcp_call_result import McpCallResult
from engineering_influence.models.mcp_server_info import McpServerInfo
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.mcp_tool_descriptor import McpToolDescriptor
from engineering_influence.models.mcp_tool_set import McpToolSet
from engineering_influence.services.interfaces.mcp_client_factory_interface import (
    McpClientFactoryInterface,
)
from engineering_influence.services.interfaces.mcp_client_interface import McpClientInterface
from engineering_influence.services.interfaces.mcp_server_probe_interface import (
    McpServerProbeInterface,
)
from engineering_influence.services.mcp_server_probe import McpServerProbe
from engineering_influence.services.tool_lock_verifier import ToolLockVerifier

EXE = "/usr/bin/server"
TOOLS = McpToolSet((McpToolDescriptor("echo", "Echoes.", {"type": "object"}),))
INFO = McpServerInfo("test-server", "1.0.0", "2025-06-18")
ENTRY = McpServerLock(
    name="files",
    command=(EXE,),
    files=((EXE, "a" * 64),),
    env=("FILES_ROOT",),
    server_name="test-server",
    server_version="1.0.0",
    tool_names=("echo",),
    tools_hash=TOOLS.digest(),
)


class Hasher(FileHasherInterface):
    def __init__(self, digest: str | None = "a" * 64) -> None:
        self.value = digest

    def digest(self, path: str) -> str | None:
        return self.value if path == EXE else None


class Transport(McpTransportInterface):
    def send(self, message: Mapping[str, Any]) -> None: ...

    def receive(self, timeout_seconds: float) -> Mapping[str, Any]:
        return {}

    def close(self) -> None: ...


class Transports(McpTransportFactoryInterface):
    def __init__(self, fail: BaseException | None = None) -> None:
        self.opened: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
        self.fail = fail

    def open(self, command: tuple[str, ...], env_names: tuple[str, ...]) -> McpTransportInterface:
        self.opened.append((command, env_names))
        if self.fail:
            raise self.fail
        return Transport()


class Remotes(McpRemoteTransportFactoryInterface):
    def __init__(self, fail: BaseException | None = None) -> None:
        self.opened: list[tuple[str, str]] = []
        self.fail = fail

    def open(self, url: str, bearer_env: str) -> McpTransportInterface:
        self.opened.append((url, bearer_env))
        if self.fail:
            raise self.fail
        return Transport()


class Client(McpClientInterface):
    def __init__(
        self,
        info: McpServerInfo = INFO,
        tools: McpToolSet = TOOLS,
        fail: BaseException | None = None,
    ) -> None:
        self.info, self.tools, self.fail = info, tools, fail
        self.closed = 0

    def initialize(self) -> McpServerInfo:
        if self.fail:
            raise self.fail
        return self.info

    def list_tools(self) -> McpToolSet:
        return self.tools

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> McpCallResult:
        raise NotImplementedError

    def close(self) -> None:
        self.closed += 1


class Clients(McpClientFactoryInterface):
    def __init__(self, client: Client) -> None:
        self.client = client
        self.transports: list[McpTransportInterface] = []

    def create(self, transport: McpTransportInterface) -> McpClientInterface:
        self.transports.append(transport)
        return self.client


def probe(
    client: Client | None = None,
    hasher: Hasher | None = None,
    transports: Transports | None = None,
    remotes: Remotes | None = None,
):
    made = Transports() if transports is None else transports
    clients = Clients(client or Client())
    return (
        McpServerProbe(
            made,
            Remotes() if remotes is None else remotes,
            clients,
            ToolLockVerifier(hasher or Hasher()),
        ),
        made,
        clients,
    )


def test_it_is_a_probe() -> None:
    assert isinstance(probe()[0], McpServerProbeInterface)


def test_inspect_starts_the_command_with_the_named_variables_and_returns_what_it_said() -> None:
    mcp, transports, clients = probe()
    inspection = mcp.inspect((EXE, "arg"), ("FILES_ROOT",))
    assert transports.opened == [((EXE, "arg"), ("FILES_ROOT",))]
    assert (inspection.info, inspection.tools) == (INFO, TOOLS)
    assert clients.client.closed == 1


def test_inspect_stops_the_server_even_when_asking_fails() -> None:
    client = Client(fail=ApplicationError(code="MCP_REPLY_INVALID", message="bad", http_status=502))
    mcp, _, _ = probe(client)
    with pytest.raises(ApplicationError, match="bad"):
        mcp.inspect((EXE,), ())
    assert client.closed == 1


def test_check_passes_when_the_files_and_the_server_are_as_locked() -> None:
    mcp, transports, _ = probe()
    assert mcp.check(ENTRY) == ()
    assert transports.opened == [((EXE,), ("FILES_ROOT",))]


def test_a_server_whose_files_changed_is_never_started() -> None:
    mcp, transports, _ = probe(hasher=Hasher("b" * 64))
    assert mcp.check(ENTRY) == (f"{EXE} has changed since it was locked",)
    assert transports.opened == []


def test_a_server_that_reports_something_else_is_a_problem() -> None:
    other = Client(info=McpServerInfo("evil", "1.0.0", "p"))
    [problem] = probe(other)[0].check(ENTRY)
    assert problem == "the server now calls itself 'evil', not 'test-server'"


def test_a_server_that_cannot_be_started_is_a_problem_not_a_crash() -> None:
    gone = ApplicationError(
        code="MCP_SERVER_START_FAILED", message="could not be started: nope", http_status=502
    )
    mcp, _, _ = probe(transports=Transports(fail=gone))
    assert mcp.check(ENTRY) == ("the server could not be checked: could not be started: nope",)


def test_a_server_that_does_not_answer_is_a_problem_not_a_crash() -> None:
    mcp, _, clients = probe(Client(fail=TransientStageError("did not answer within 30 seconds")))
    assert mcp.check(ENTRY) == (
        "the server could not be checked: did not answer within 30 seconds",
    )
    assert clients.client.closed == 1


# ------------------------------------------------------------------------------ remote servers
REMOTE = McpServerLock(
    name="docs",
    command=(),
    files=(),
    env=(),
    server_name="test-server",
    server_version="1.0.0",
    tool_names=("echo",),
    tools_hash=TOOLS.digest(),
    url="https://mcp.example.com/mcp",
    bearer_env="DOCS_TOKEN",
)


def test_inspect_remote_contacts_the_address_with_the_named_variable_and_stops_when_done() -> None:
    remotes = Remotes()
    mcp, transports, clients = probe(remotes=remotes)
    inspection = mcp.inspect_remote("https://mcp.example.com/mcp", "DOCS_TOKEN")
    assert remotes.opened == [("https://mcp.example.com/mcp", "DOCS_TOKEN")]
    assert transports.opened == []
    assert (inspection.info, inspection.tools) == (INFO, TOOLS)
    assert clients.client.closed == 1


def test_inspect_remote_stops_the_session_even_when_asking_fails() -> None:
    client = Client(fail=ApplicationError(code="MCP_REPLY_INVALID", message="bad", http_status=502))
    mcp, _, _ = probe(client)
    with pytest.raises(ApplicationError, match="bad"):
        mcp.inspect_remote("https://mcp.example.com/mcp", "")
    assert client.closed == 1


def test_a_remote_server_has_no_files_so_it_is_checked_by_what_it_says_alone() -> None:
    remotes = Remotes()
    mcp, transports, _ = probe(hasher=Hasher(None), remotes=remotes)
    assert mcp.check(REMOTE) == ()
    assert remotes.opened == [("https://mcp.example.com/mcp", "DOCS_TOKEN")]
    assert transports.opened == []


def test_a_remote_server_that_advertises_other_tools_is_a_problem() -> None:
    other = Client(tools=McpToolSet((McpToolDescriptor("echo", "Reworded.", {"type": "object"}),)))
    [problem] = probe(other)[0].check(REMOTE)
    assert problem.startswith("the tools the server advertises have changed")


def test_a_remote_server_that_cannot_be_reached_is_a_problem_not_a_crash() -> None:
    refused = ApplicationError(
        code="MCP_URL_REFUSED",
        message="mcp.example.com refused: non_public_address",
        http_status=503,
    )
    mcp, _, _ = probe(remotes=Remotes(fail=refused))
    assert mcp.check(REMOTE) == (
        "the server could not be checked: mcp.example.com refused: non_public_address",
    )
