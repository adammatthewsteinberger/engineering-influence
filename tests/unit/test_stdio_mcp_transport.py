# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""StdioMcpTransport against a real server process: the happy path, and every way a server can misbehave."""

import json
import os
import signal
import sys
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.process.interfaces.process_meter_interface import (
    ProcessMeterInterface,
)
from engineering_influence.infrastructure.tools.stdio_mcp_transport import StdioMcpTransport
from engineering_influence.infrastructure.tools.stdio_mcp_transport_factory import (
    StdioMcpTransportFactory,
)
from engineering_influence.interfaces.mcp_transport_factory_interface import (
    McpTransportFactoryInterface,
)
from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface
from engineering_influence.models.tool_limits import ToolLimits
from engineering_influence.services.mcp_client import McpClient

SERVER = Path(__file__).resolve().parents[1] / "fixtures" / "mcp" / "stdio_server.py"
ROOMY = ToolLimits(timeout_seconds=60, max_memory_bytes=2**31, max_disk_bytes=2**30)
MIB = 2**20


class Meter(ProcessMeterInterface):
    def __init__(self, memory: int = 0, disk: int = 0) -> None:
        self.memory, self.disk = memory, disk

    def memory_bytes(self, group: int) -> int:
        return self.memory

    def disk_bytes(self, directory: Path) -> int:
        return self.disk


def factory(
    limits: ToolLimits = ROOMY,
    environ: Mapping[str, str] | None = None,
    meter: ProcessMeterInterface | None = None,
) -> StdioMcpTransportFactory:
    return StdioMcpTransportFactory(limits, environ or {}, meter, sample_seconds=0.05)


@contextmanager
def server(
    mode: str = "ok", *extra: str, env_names: tuple[str, ...] = (), **options: Any
) -> Iterator[McpTransportInterface]:
    transport = factory(**options).open((sys.executable, str(SERVER), mode, *extra), env_names)
    try:
        yield transport
    finally:
        transport.close()


def initialize(transport: McpTransportInterface, ident: int = 1) -> Mapping[str, Any]:
    transport.send({"jsonrpc": "2.0", "id": ident, "method": "initialize", "params": {}})
    return transport.receive(10)


def call_tool(mcp: McpClient, name: str) -> str:
    return mcp.call_tool(name, {}).text


def client_for(transport: McpTransportInterface) -> McpClient:
    return McpClient(transport, "tests", "1", 10)


# --------------------------------------------------------------------------- happy path
def test_the_factory_and_transport_are_the_ports() -> None:
    assert isinstance(factory(), McpTransportFactoryInterface)
    with server() as transport:
        assert isinstance(transport, McpTransportInterface)


def test_a_message_goes_out_and_the_answer_comes_back() -> None:
    with server() as transport:
        reply = initialize(transport)
    assert reply["id"] == 1 and reply["result"]["serverInfo"] == {
        "name": "test-server",
        "version": "1.0.0",
    }


def test_a_real_client_can_initialize_list_and_call_over_it() -> None:
    with server() as transport:
        mcp = client_for(transport)
        info = mcp.initialize()
        tools = mcp.list_tools()
        said = mcp.call_tool("echo", {"text": "héllo wörld ✓"})
    assert (info.name, info.version) == ("test-server", "1.0.0")
    assert tools.names() == ("echo", "env_names", "grandchild", "last_reply", "where")
    assert (said.text, said.is_error) == ("héllo wörld ✓", False)


def test_an_error_flag_from_the_server_survives_the_trip() -> None:
    with server() as transport:
        mcp = client_for(transport)
        mcp.initialize()
        result = mcp.call_tool("nonexistent", {})
    assert result.is_error and result.text == "no tool nonexistent"


def test_a_request_the_server_makes_is_refused_and_the_server_is_told_so() -> None:
    with server("sampling") as transport:
        mcp = client_for(transport)
        mcp.initialize()
        mcp.list_tools()
        heard = call_tool(mcp, "last_reply")
    assert '"id": 99' in heard and "-32601" in heard and "method not found" in heard


# --------------------------------------------------------------------- the environment
def test_a_server_sees_only_the_allow_list_and_what_is_named() -> None:
    environ = {"PATH": "/usr/bin", "SECRET_TOKEN": "s3cret", "FILES_ROOT": "/data"}
    with server(environ=environ, env_names=("FILES_ROOT",)) as transport:
        mcp = client_for(transport)
        mcp.initialize()
        names = call_tool(mcp, "env_names").split(",")
    assert "SECRET_TOKEN" not in names
    assert "FILES_ROOT" in names and "PATH" in names and "HOME" in names


def test_the_servers_directory_home_and_temp_are_its_own_and_go_with_it() -> None:
    with server() as transport:
        mcp = client_for(transport)
        mcp.initialize()
        where = call_tool(mcp, "where")
    seen = json.loads(where)
    real = [os.path.realpath(seen[key]) for key in ("cwd", "home", "tmp")]
    assert real[0] == real[1] == real[2]
    assert "ei-mcp-" in seen["cwd"]
    assert not Path(seen["cwd"]).exists()


# -------------------------------------------------------------------------- stopping it
def test_closing_kills_the_whole_process_group_including_what_it_started() -> None:
    with server() as transport:
        mcp = client_for(transport)
        mcp.initialize()
        child = int(call_tool(mcp, "grandchild"))
        os.kill(child, 0)  # it is alive
    for _ in range(100):
        try:
            os.kill(child, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    pytest.fail("the grandchild outlived the server")


def test_closing_twice_is_harmless() -> None:
    transport = factory().open((sys.executable, str(SERVER)), ())
    transport.close()
    transport.close()


def test_a_server_that_cannot_be_started_is_an_error_and_leaves_no_directory() -> None:
    import tempfile

    pattern = Path(tempfile.gettempdir())
    before = {p.name for p in pattern.glob("ei-mcp-*")}
    with pytest.raises(ApplicationError) as error:
        factory().open(("/nonexistent/server",), ())
    assert (error.value.code, error.value.http_status) == ("MCP_SERVER_START_FAILED", 502)
    assert "could not be started" in error.value.message
    assert {p.name for p in pattern.glob("ei-mcp-*")} == before


def test_a_missing_named_variable_stops_the_start_before_anything_runs() -> None:
    with pytest.raises(ApplicationError) as error:
        factory().open((sys.executable, str(SERVER)), ("NOT_SET_ANYWHERE",))
    assert error.value.code == "TOOL_ENV_MISSING"


# --------------------------------------------------------------------- a server that fails
def test_a_server_that_exits_at_once_is_reported_as_closed() -> None:
    with server("exit") as transport, pytest.raises(ApplicationError) as error:
        transport.receive(10)
    assert (error.value.code, error.value.http_status) == ("MCP_SERVER_CLOSED", 502)
    assert error.value.message == "the MCP server closed its output."


def test_what_it_said_on_standard_error_is_quoted() -> None:
    with server("stderr-exit") as transport, pytest.raises(ApplicationError) as error:
        transport.receive(10)
    assert error.value.code == "MCP_SERVER_CLOSED"
    assert "Its last words on stderr: 'boom: bad config'" in error.value.message


def test_the_end_of_the_output_stays_the_end() -> None:
    with server("exit") as transport:
        for _ in range(3):
            with pytest.raises(ApplicationError, match="closed its output"):
                transport.receive(10)


def test_sending_to_a_server_that_has_gone_is_an_error_not_a_crash() -> None:
    with server("exit") as transport:
        with pytest.raises(ApplicationError):
            transport.receive(10)
        with pytest.raises(ApplicationError, match="closed its output"):
            for _ in range(50):
                transport.send({"jsonrpc": "2.0", "id": 1, "method": "ping"})
                time.sleep(0.02)


def test_a_server_that_does_not_answer_in_time_is_a_transient_failure() -> None:
    with server("hang") as transport:
        transport.send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        with pytest.raises(TransientStageError, match="did not answer within 0.2 seconds"):
            transport.receive(0.2)


@pytest.mark.parametrize(
    ("mode", "what"),
    [("bad-json", "a line that is not JSON"), ("array", "JSON that is not an object")],
)
def test_a_line_that_is_not_a_json_object_is_refused(mode: str, what: str) -> None:
    with server(mode) as transport:
        mcp = client_for(transport)
        mcp.initialize()
        with pytest.raises(ApplicationError) as error:
            mcp.list_tools()
    assert (error.value.code, error.value.message) == (
        "MCP_REPLY_INVALID",
        f"the MCP server sent {what}",
    )


def test_a_line_longer_than_four_mebibytes_stops_the_server() -> None:
    with server("bigline") as transport:
        mcp = client_for(transport)
        mcp.initialize()
        with pytest.raises(ApplicationError) as error:
            mcp.list_tools()
    assert error.value.code == "MCP_SERVER_LIMIT"
    assert (
        f"sent a line longer than {StdioMcpTransport.MAX_LINE_BYTES} bytes and was stopped"
        in error.value.message
    )


def test_a_server_that_floods_is_slowed_by_the_queue_and_still_closes_cleanly() -> None:
    with server("flood") as transport:
        time.sleep(0.5)  # the queue fills and the reader waits on it
        assert isinstance(transport, StdioMcpTransport)
        assert transport._lines.qsize() == StdioMcpTransport.QUEUE_LINES
        message = transport.receive(10)
        assert message["method"] == "notifications/message"


def test_blank_lines_between_messages_are_not_messages() -> None:
    with server("blank-lines") as transport:
        mcp = client_for(transport)
        assert mcp.initialize().name == "test-server"
        assert mcp.list_tools().names()[0] == "echo"


# --------------------------------------------------------------------------------- limits
def idle(limits: ToolLimits, meter: ProcessMeterInterface) -> Any:
    return server(limits=limits, meter=meter)


def test_memory_over_the_limit_stops_the_server_and_says_how_much() -> None:
    limits = ToolLimits(timeout_seconds=60, max_memory_bytes=1 * MIB, max_disk_bytes=2**30)
    with (
        idle(limits, Meter(memory=10 * MIB)) as transport,
        pytest.raises(ApplicationError) as error,
    ):
        transport.receive(10)
    assert error.value.code == "MCP_SERVER_LIMIT"
    assert (
        error.value.message
        == "the MCP server used 10 MiB of memory, over its limit of 1 MiB and was stopped"
    )


def test_disk_over_the_limit_stops_the_server_and_says_how_much() -> None:
    limits = ToolLimits(timeout_seconds=60, max_memory_bytes=2**31, max_disk_bytes=1 * MIB)
    with idle(limits, Meter(disk=7 * MIB)) as transport, pytest.raises(ApplicationError) as error:
        transport.receive(10)
    assert (
        error.value.message
        == "the MCP server wrote 7 MiB to disk, over its limit of 1 MiB and was stopped"
    )


def test_a_session_that_runs_past_its_time_limit_is_stopped() -> None:
    limits = ToolLimits(timeout_seconds=0.3, max_memory_bytes=2**31, max_disk_bytes=2**30)
    with idle(limits, Meter()) as transport, pytest.raises(ApplicationError) as error:
        transport.receive(10)
    assert (
        error.value.message
        == "the MCP server ran past its session limit of 0.3 seconds and was stopped"
    )


def test_exactly_at_the_limits_is_still_allowed() -> None:
    limits = ToolLimits(timeout_seconds=60, max_memory_bytes=5 * MIB, max_disk_bytes=6 * MIB)
    with idle(limits, Meter(memory=5 * MIB, disk=6 * MIB)) as transport:
        time.sleep(0.4)  # many sampling intervals
        assert initialize(transport)["id"] == 1


def test_a_server_stopped_for_a_limit_cannot_be_sent_to() -> None:
    limits = ToolLimits(timeout_seconds=60, max_memory_bytes=1 * MIB, max_disk_bytes=2**30)
    with idle(limits, Meter(memory=10 * MIB)) as transport:
        with pytest.raises(ApplicationError):
            transport.receive(10)
        with pytest.raises(ApplicationError, match="over its limit"):
            for _ in range(50):
                transport.send({"jsonrpc": "2.0", "id": 1, "method": "ping"})
                time.sleep(0.02)


def test_the_first_limit_passed_is_the_one_reported() -> None:
    limits = ToolLimits(timeout_seconds=60, max_memory_bytes=1 * MIB, max_disk_bytes=1 * MIB)
    meter = Meter(memory=10 * MIB, disk=10 * MIB)
    with (
        idle(limits, meter) as transport,
        pytest.raises(ApplicationError, match="used 10 MiB of memory"),
    ):
        transport.receive(10)


def test_the_sampling_interval_is_more_than_zero() -> None:
    with pytest.raises(ValueError, match="more than zero"):
        StdioMcpTransport((sys.executable,), {}, ROOMY, Path("/tmp"), None, 0)


def test_the_default_meter_runs_and_a_modest_server_stays_inside_the_limits() -> None:
    real = StdioMcpTransportFactory(ROOMY, {}, None, 0.05)
    transport = real.open((sys.executable, str(SERVER)), ())
    try:
        time.sleep(0.3)
        assert initialize(transport)["id"] == 1
    finally:
        transport.close()


def test_closing_removes_the_working_directory() -> None:
    transport = factory().open((sys.executable, str(SERVER)), ())
    mcp = client_for(transport)
    mcp.initialize()
    cwd = json.loads(call_tool(mcp, "where"))["cwd"]
    assert Path(cwd).is_dir()
    mcp.close()
    assert not Path(cwd).exists()


def test_a_line_of_exactly_the_maximum_size_is_allowed() -> None:
    with server("maxline") as transport:
        mcp = client_for(transport)
        mcp.initialize()
        assert mcp.list_tools().names() == ()


def test_json_nested_too_deeply_to_read_is_refused_not_a_crash() -> None:
    with server("deep") as transport:
        mcp = client_for(transport)
        mcp.initialize()
        with pytest.raises(ApplicationError, match="sent a line that is not JSON"):
            mcp.list_tools()


def test_the_first_reason_a_server_was_stopped_is_the_one_it_keeps() -> None:
    meter = Meter()
    limits = ToolLimits(timeout_seconds=60, max_memory_bytes=1 * MIB, max_disk_bytes=2**30)
    with server("bigline", limits=limits, meter=meter) as transport:
        mcp = client_for(transport)
        mcp.initialize()
        with pytest.raises(ApplicationError, match="sent a line longer than"):
            mcp.list_tools()
        meter.memory = 10 * MIB  # a second reason, after the first
        time.sleep(0.3)  # the watchdog sees it
        with pytest.raises(ApplicationError, match="sent a line longer than"):
            transport.receive(5)


class Kills:
    """Records each signal sent to a process group, and sends it."""

    def __init__(self) -> None:
        self.calls: list[tuple[int, int]] = []

    def __call__(self, group: int, signum: int) -> None:
        self.calls.append((group, signum))
        os.killpg(group, signum)


def raw(kills: Kills) -> StdioMcpTransport:
    import tempfile

    workdir = Path(tempfile.mkdtemp(prefix="ei-mcp-"))
    return StdioMcpTransport((sys.executable, str(SERVER)), {}, ROOMY, workdir, None, 0.05, kills)


def test_the_first_close_kills_the_group_and_a_second_signals_nothing() -> None:
    kills = Kills()
    transport = raw(kills)
    transport.close()
    first = len(kills.calls)
    assert first >= 1 and all(signum == signal.SIGKILL for _, signum in kills.calls)
    transport.close()
    assert len(kills.calls) == first  # the leader is reaped by now: its id may be a stranger's


def test_every_helper_thread_has_finished_once_it_is_closed_even_with_a_full_queue() -> None:
    transport = factory().open((sys.executable, str(SERVER), "flood"), ())
    assert isinstance(transport, StdioMcpTransport)
    time.sleep(0.5)  # the queue is full and the reader is waiting to put into it
    transport.close()
    assert not [thread for thread in transport._threads if thread.is_alive()]
