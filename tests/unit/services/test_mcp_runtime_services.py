# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""The connection, the launcher, the tool, its factory and the fleet that start locked servers for a run."""

import threading
import time
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
from engineering_influence.interfaces.tool_grants_interface import ToolGrantsInterface
from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.models.mcp_call_result import McpCallResult
from engineering_influence.models.mcp_server_info import McpServerInfo
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.mcp_tool_descriptor import McpToolDescriptor
from engineering_influence.models.mcp_tool_set import McpToolSet
from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.services.interfaces.mcp_client_factory_interface import (
    McpClientFactoryInterface,
)
from engineering_influence.services.interfaces.mcp_client_interface import McpClientInterface
from engineering_influence.services.interfaces.mcp_connection_interface import (
    McpConnectionInterface,
)
from engineering_influence.services.interfaces.mcp_server_launcher_interface import (
    McpServerLauncherInterface,
)
from engineering_influence.services.interfaces.mcp_tool_factory_interface import (
    McpToolFactoryInterface,
)
from engineering_influence.services.interfaces.tool_server_fleet_interface import (
    ToolServerFleetInterface,
)
from engineering_influence.services.lock_tool_grants import LockToolGrants
from engineering_influence.services.mcp_connection import McpConnection
from engineering_influence.services.mcp_server_launcher import McpServerLauncher
from engineering_influence.services.mcp_tool import McpTool
from engineering_influence.services.mcp_tool_factory import McpToolFactory
from engineering_influence.services.tool_lock_verifier import ToolLockVerifier
from engineering_influence.services.tool_server_fleet import ToolServerFleet

EXE = "/usr/bin/server"
OBJECT = {"type": "object", "properties": {"text": {"type": "string"}}}
READ = McpToolDescriptor("read", "Reads a file.", OBJECT)
WRITE = McpToolDescriptor("write", "Writes a file.", OBJECT)
TOOLS = McpToolSet((READ, WRITE))
INFO = McpServerInfo("test-server", "1.0.0", "2025-06-18")


def lock_entry(
    name: str = "files", tools: McpToolSet = TOOLS, grants: Any = (), env: tuple[str, ...] = ()
) -> McpServerLock:
    return McpServerLock(
        name=name,
        command=(EXE,),
        files=((EXE, "a" * 64),),
        env=env,
        server_name="test-server",
        server_version="1.0.0",
        tool_names=tools.names(),
        tools_hash=tools.digest(),
        grants=grants,
    )


class Client(McpClientInterface):
    def __init__(
        self,
        info: McpServerInfo = INFO,
        tools: McpToolSet = TOOLS,
        fail: BaseException | None = None,
    ) -> None:
        self.info, self.tools, self.fail = info, tools, fail
        self.closed = 0
        self.called: list[tuple[str, Mapping[str, Any]]] = []
        self.answer = McpCallResult("ok", False)

    def initialize(self) -> McpServerInfo:
        if self.fail:
            raise self.fail
        return self.info

    def list_tools(self) -> McpToolSet:
        return self.tools

    def call_tool(self, name: str, arguments: Mapping[str, Any]) -> McpCallResult:
        self.called.append((name, arguments))
        return self.answer

    def close(self) -> None:
        self.closed += 1


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


class Clients(McpClientFactoryInterface):
    def __init__(self, client: Client) -> None:
        self.client = client

    def create(self, transport: McpTransportInterface) -> McpClientInterface:
        return self.client


class Hasher(FileHasherInterface):
    def __init__(self, digest: str | None = "a" * 64) -> None:
        self.value = digest

    def digest(self, path: str) -> str | None:
        return self.value if path == EXE else None


def launcher(
    client: Client | None = None,
    transports: Transports | None = None,
    hasher: Hasher | None = None,
    remotes: Remotes | None = None,
):
    used = client or Client()
    made = transports or Transports()
    return (
        McpServerLauncher(
            made,
            Remotes() if remotes is None else remotes,
            Clients(used),
            ToolLockVerifier(hasher or Hasher()),
        ),
        made,
        used,
    )


# ------------------------------------------------------------------------------ connection
def test_a_connection_reports_its_server_and_tools_and_passes_calls_on() -> None:
    client = Client()
    connection = McpConnection("files", client, TOOLS)
    assert isinstance(connection, McpConnectionInterface)
    assert connection.server() == "files" and connection.tools() is TOOLS
    assert connection.call("read", {"text": "x"}).text == "ok"
    assert client.called == [("read", {"text": "x"})]


def test_calls_through_one_connection_never_overlap() -> None:
    class Slow(Client):
        def __init__(self) -> None:
            super().__init__()
            self.inside = 0
            self.most = 0

        def call_tool(self, name: str, arguments: Mapping[str, Any]) -> McpCallResult:
            self.inside += 1
            self.most = max(self.most, self.inside)
            time.sleep(0.05)
            self.inside -= 1
            return super().call_tool(name, arguments)

    client = Slow()
    connection = McpConnection("files", client, TOOLS)
    threads = [threading.Thread(target=connection.call, args=("read", {})) for _ in range(6)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert len(client.called) == 6 and client.most == 1


def test_closing_stops_the_server_at_once_even_while_a_call_is_in_flight() -> None:
    release = threading.Event()
    entered = threading.Event()

    class Stuck(Client):
        def call_tool(self, name: str, arguments: Mapping[str, Any]) -> McpCallResult:
            entered.set()
            release.wait(10)
            return super().call_tool(name, arguments)

    client = Stuck()
    connection = McpConnection("files", client, TOOLS)
    caller = threading.Thread(target=connection.call, args=("read", {}))
    caller.start()
    assert entered.wait(5)
    connection.close()  # must not wait for the call
    assert client.closed == 1
    release.set()
    caller.join()


# --------------------------------------------------------------------------------- the tool
def test_a_tool_is_the_servers_description_called_through_the_connection() -> None:
    client = Client()
    tool = McpTool(McpConnection("files", client, TOOLS), READ)
    assert isinstance(tool, ToolInterface)
    definition = tool.definition()
    assert (definition.name, definition.description) == ("files__read", "Reads a file.")
    assert definition.parameters == OBJECT
    assert tool.invoke({"text": "hi"}) == "ok"
    assert client.called == [("read", {"text": "hi"})]


def test_its_revision_is_the_hash_of_the_servers_tools() -> None:
    tool = McpTool(McpConnection("files", Client(), TOOLS), READ)
    assert tool.revision() == TOOLS.digest()
    other = McpTool(McpConnection("files", Client(), McpToolSet((READ,))), READ)
    assert other.revision() != tool.revision()


def test_an_answer_the_server_calls_an_error_is_an_application_error_with_its_text() -> None:
    client = Client()
    client.answer = McpCallResult("no such file", True)
    with pytest.raises(ApplicationError) as error:
        McpTool(McpConnection("files", client, TOOLS), READ).invoke({})
    assert (error.value.code, error.value.http_status, error.value.message) == (
        "MCP_TOOL_ERROR",
        502,
        "no such file",
    )


def test_an_error_with_no_text_still_says_something() -> None:
    client = Client()
    client.answer = McpCallResult("", True)
    with pytest.raises(ApplicationError, match="reported an error and said nothing"):
        McpTool(McpConnection("files", client, TOOLS), READ).invoke({})


def test_a_tool_has_no_opinion_about_what_it_was_shown_so_its_results_prove_nothing() -> None:
    tool = McpTool(McpConnection("files", Client(), TOOLS), READ)
    assert tool.refuses({"text": "x"}, "") == "" and tool.shown("https://a.test/") == ""


# ------------------------------------------------------------------------------ the factory
def test_the_factory_makes_a_tool_for_each_offerable_tool_in_name_order() -> None:
    odd = McpToolDescriptor("bad name", "A name no provider accepts.", OBJECT)
    text = McpToolDescriptor("text", "Takes text.", {"type": "string"})
    connection = McpConnection("files", Client(), McpToolSet((WRITE, odd, text, READ)))
    tools = McpToolFactory().create(connection)
    assert isinstance(McpToolFactory(), McpToolFactoryInterface)
    assert [tool.definition().name for tool in tools] == ["files__read", "files__write"]


# ----------------------------------------------------------------------------- the launcher
def test_a_server_that_is_as_locked_is_started_and_connected() -> None:
    mcp, transports, client = launcher()
    connection = mcp.start(lock_entry(env=("FILES_ROOT",)))
    assert isinstance(mcp, McpServerLauncherInterface)
    assert transports.opened == [((EXE,), ("FILES_ROOT",))]
    assert connection.server() == "files" and connection.tools() is TOOLS and client.closed == 0


def test_a_server_whose_files_changed_is_refused_and_never_started() -> None:
    mcp, transports, _ = launcher(hasher=Hasher("b" * 64))
    with pytest.raises(ApplicationError) as error:
        mcp.start(lock_entry())
    assert (error.value.code, error.value.http_status) == ("TOOL_LOCK_MISMATCH", 503)
    assert error.value.message == (
        f"locked server 'files' is not what was approved: {EXE} has changed since it was locked"
    )
    assert transports.opened == []


def test_a_server_that_says_something_else_is_stopped_and_refused() -> None:
    other = Client(info=McpServerInfo("evil-server", "1.0.0", "p"))
    mcp, _, _ = launcher(other)
    with pytest.raises(ApplicationError) as error:
        mcp.start(lock_entry())
    assert (error.value.code, error.value.http_status) == ("TOOL_LOCK_MISMATCH", 503)
    assert error.value.message == (
        "locked server 'files' is not what was approved: "
        "the server now calls itself 'evil-server', not 'test-server'"
    )
    assert other.closed == 1


def test_a_server_whose_tools_changed_is_stopped_and_refused() -> None:
    changed = Client(tools=McpToolSet((READ,)))
    mcp, _, _ = launcher(changed)
    with pytest.raises(ApplicationError, match="tools the server advertises have changed"):
        mcp.start(lock_entry())
    assert changed.closed == 1


def test_every_problem_is_in_the_message() -> None:
    other = Client(info=McpServerInfo("evil", "9", "p"), tools=McpToolSet((READ,)))
    mcp, _, _ = launcher(other)
    with pytest.raises(ApplicationError) as error:
        mcp.start(lock_entry())
    assert error.value.message.count(";") == 2


def test_a_granted_tool_that_cannot_be_offered_to_a_model_is_refused_and_the_server_stopped() -> (
    None
):
    text = McpToolDescriptor("text", "Takes text.", {"type": "string"})
    tools = McpToolSet((READ, text))
    entry = lock_entry(tools=tools, grants=(("research", ("read", "text")),))
    client = Client(tools=tools)
    mcp, _, _ = launcher(client)
    with pytest.raises(ApplicationError) as error:
        mcp.start(entry)
    assert error.value.code == "TOOL_LOCK_MISMATCH"
    assert "the granted tool 'text' cannot be offered to a model" in error.value.message
    assert client.closed == 1


def test_a_granted_tool_that_can_be_offered_is_fine() -> None:
    mcp, _, client = launcher()
    mcp.start(lock_entry(grants=(("research", ("read",)),)))
    assert client.closed == 0


def test_a_server_that_does_not_answer_is_unavailable_and_stopped() -> None:
    slow = Client(fail=TransientStageError("did not answer within 30 seconds"))
    mcp, _, _ = launcher(slow)
    with pytest.raises(ApplicationError) as error:
        mcp.start(lock_entry())
    assert (error.value.code, error.value.http_status) == ("TOOL_SERVER_UNAVAILABLE", 503)
    assert (
        error.value.message
        == "locked server 'files' could not be started: did not answer within 30 seconds"
    )
    assert slow.closed == 1


def test_a_server_that_fails_keeps_its_error_code_with_the_server_named() -> None:
    broken = Client(
        fail=ApplicationError(
            code="MCP_SERVER_CLOSED", message="the MCP server closed its output.", http_status=502
        )
    )
    mcp, _, _ = launcher(broken)
    with pytest.raises(ApplicationError) as error:
        mcp.start(lock_entry())
    assert (error.value.code, error.value.http_status) == ("MCP_SERVER_CLOSED", 503)
    assert (
        error.value.message
        == "locked server 'files' could not be started: the MCP server closed its output."
    )
    assert broken.closed == 1


def test_a_server_that_cannot_be_opened_at_all_is_unavailable() -> None:
    gone = ApplicationError(
        code="MCP_SERVER_START_FAILED", message="could not be started: nope", http_status=502
    )
    mcp, _, client = launcher(transports=Transports(fail=gone))
    with pytest.raises(ApplicationError) as error:
        mcp.start(lock_entry())
    assert error.value.code == "MCP_SERVER_START_FAILED" and "'files'" in error.value.message
    assert client.closed == 0  # there was no client to stop


# ---------------------------------------------------------------------------------- the fleet
class Launcher(McpServerLauncherInterface):
    def __init__(self, fail_on: str | None = None) -> None:
        self.started: list[str] = []
        self.closed: list[str] = []
        self.fail_on = fail_on

    def verify_files(self, entry: McpServerLock) -> None:
        if entry.name == self.fail_on:
            raise ApplicationError(
                code="TOOL_LOCK_MISMATCH", message=f"{entry.name} changed", http_status=503
            )

    def start(self, entry: McpServerLock) -> McpConnectionInterface:
        if entry.name == self.fail_on:
            raise ApplicationError(
                code="TOOL_LOCK_MISMATCH", message=f"{entry.name} changed", http_status=503
            )
        self.started.append(entry.name)
        launched = self

        class Connection(McpConnection):
            def close(self) -> None:
                launched.closed.append(entry.name)

        return Connection(entry.name, Client(), TOOLS)


def fleet(launch: Launcher) -> ToolServerFleet:
    return ToolServerFleet(launch, McpToolFactory())


def test_verifying_starts_nothing_and_each_server_starts_once_on_first_use() -> None:
    launch = Launcher()
    group = fleet(launch)
    lock = ToolLock((lock_entry("zed"), lock_entry("alpha")))
    group.verify(lock)
    assert isinstance(group, ToolServerFleetInterface)
    assert launch.started == [] and group.running() == ()
    tools = group.activate(lock_entry("alpha"))
    assert [tool.definition().name for tool in tools] == ["alpha__read", "alpha__write"]
    assert group.activate(lock_entry("alpha")) == ()
    assert launch.started == ["alpha"] and group.running() == ("alpha",)


def test_a_file_that_changed_is_refused_at_verification_before_anything_starts() -> None:
    launch = Launcher(fail_on="mid")
    group = fleet(launch)
    with pytest.raises(ApplicationError, match="mid changed"):
        group.verify(ToolLock((lock_entry("alpha"), lock_entry("mid"))))
    assert launch.started == [] and group.running() == ()


def test_a_server_that_cannot_start_raises_and_leaves_the_others_running() -> None:
    launch = Launcher(fail_on="mid")
    group = fleet(launch)
    group.activate(lock_entry("alpha"))
    with pytest.raises(ApplicationError, match="mid changed"):
        group.activate(lock_entry("mid"))
    assert group.running() == ("alpha",) and launch.closed == []


def test_closing_stops_the_servers_in_reverse_order_and_a_second_close_does_nothing() -> None:
    launch = Launcher()
    group = fleet(launch)
    for name in ("a", "b", "c"):
        group.activate(lock_entry(name))
    group.close()
    assert launch.closed == ["c", "b", "a"] and group.running() == ()
    group.close()
    assert launch.closed == ["c", "b", "a"]


def test_an_empty_lock_verifies_and_starts_nothing() -> None:
    launch = Launcher()
    group = fleet(launch)
    group.verify(ToolLock())
    assert launch.started == [] and group.running() == ()


# ------------------------------------------------------------------------------- the grants
def test_the_grants_are_what_the_lock_says_and_nothing_else() -> None:
    lock = ToolLock((lock_entry("files", grants=(("research", ("read", "write")),)),))
    grants = LockToolGrants(lock)
    assert isinstance(grants, ToolGrantsInterface)
    assert grants.for_stage("research") == ("files__read", "files__write")
    assert grants.for_stage("outline") == ()
    assert LockToolGrants(ToolLock()).for_stage("research") == ()


# ----------------------------------------------------------------- a remote server
def remote_entry(tools: McpToolSet = TOOLS, grants: Any = ()) -> McpServerLock:
    return McpServerLock(
        name="docs",
        command=(),
        files=(),
        env=(),
        server_name="test-server",
        server_version="1.0.0",
        tool_names=tools.names(),
        tools_hash=tools.digest(),
        grants=grants,
        url="https://mcp.example.com/mcp",
        bearer_env="DOCS_TOKEN",
    )


def test_a_remote_server_is_contacted_at_its_address_and_never_started_as_a_command() -> None:
    remotes = Remotes()
    mcp, transports, client = launcher(remotes=remotes, hasher=Hasher(None))
    connection = mcp.start(remote_entry())
    assert remotes.opened == [("https://mcp.example.com/mcp", "DOCS_TOKEN")]
    assert transports.opened == []
    assert connection.server() == "docs" and connection.tools() is TOOLS and client.closed == 0


def test_a_local_server_is_never_contacted_over_the_network() -> None:
    remotes = Remotes()
    launcher(remotes=remotes)[0].start(lock_entry())
    assert remotes.opened == []


def test_a_remote_server_that_advertises_other_tools_is_closed_and_refused() -> None:
    changed = Client(tools=McpToolSet((READ,)))
    mcp, _, _ = launcher(changed)
    with pytest.raises(ApplicationError, match="tools the server advertises have changed"):
        mcp.start(remote_entry())
    assert changed.closed == 1


def test_a_remote_address_the_policy_refuses_is_unavailable_with_its_own_code() -> None:
    refused = ApplicationError(
        code="MCP_URL_REFUSED",
        message="mcp.example.com refused: non_public_address",
        http_status=503,
    )
    mcp, _, _ = launcher(remotes=Remotes(fail=refused))
    with pytest.raises(ApplicationError) as error:
        mcp.start(remote_entry())
    assert (error.value.code, error.value.http_status) == ("MCP_URL_REFUSED", 503)
    assert error.value.message == (
        "locked server 'docs' could not be started: mcp.example.com refused: non_public_address"
    )


class Unbuildable(McpToolFactoryInterface):
    def create(self, connection: McpConnectionInterface) -> tuple[ToolInterface, ...]:
        raise ApplicationError(code="TOOL_LOCK_MISMATCH", message="no tools", http_status=503)


def test_a_server_whose_tools_cannot_be_made_is_stopped_again_and_not_kept() -> None:
    launch = Launcher()
    group = ToolServerFleet(launch, Unbuildable())
    with pytest.raises(ApplicationError, match="no tools"):
        group.activate(lock_entry("alpha"))
    assert launch.started == ["alpha"] and launch.closed == ["alpha"]
    assert group.running() == ()
