# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""McpClient: the protocol it speaks, what it refuses to offer, and what it does with a hostile server."""

from collections.abc import Mapping
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface
from engineering_influence.models.mcp_server_info import McpServerInfo
from engineering_influence.models.mcp_tool_set import McpToolSet
from engineering_influence.services.interfaces.mcp_client_interface import McpClientInterface
from engineering_influence.services.mcp_client import McpClient


class Wire(McpTransportInterface):
    """A transport that plays back a script and keeps what the client sent."""

    def __init__(self, *incoming: Any) -> None:
        self.incoming = list(incoming)
        self.sent: list[dict[str, Any]] = []
        self.timeouts: list[float] = []
        self.closed = 0

    def send(self, message: Mapping[str, Any]) -> None:
        self.sent.append(dict(message))

    def receive(self, timeout_seconds: float) -> Mapping[str, Any]:
        self.timeouts.append(timeout_seconds)
        item = self.incoming.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item  # type: ignore[no-any-return]

    def close(self) -> None:
        self.closed += 1


def answer(ident: int, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": ident, "result": result}


def fail(ident: int, message: Any = "boom", code: int = -32000) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": ident, "error": {"code": code, "message": message}}


def hello(protocol: str = "2025-06-18", **changes: Any) -> dict[str, Any]:
    result = {
        "protocolVersion": protocol,
        "serverInfo": {"name": "files-server", "version": "1.2.0"},
    }
    return {**result, **changes}


def client(*incoming: Any, timeout: float = 30.0) -> tuple[McpClient, Wire]:
    wire = Wire(*incoming)
    return McpClient(wire, "engineering-influence", "9.9", timeout), wire


def refused(call: Any, code: str) -> str:
    with pytest.raises(ApplicationError) as error:
        call()
    assert (error.value.code, error.value.http_status) == (code, 502)
    return error.value.message


def test_it_is_an_mcp_client() -> None:
    assert isinstance(client()[0], McpClientInterface)


# ------------------------------------------------------------------------------ initialize
def test_initialize_announces_no_capabilities_then_says_it_is_initialized() -> None:
    mcp, wire = client(answer(1, hello()))
    info = mcp.initialize()
    assert info == McpServerInfo("files-server", "1.2.0", "2025-06-18")
    assert wire.sent == [
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "engineering-influence", "version": "9.9"},
            },
        },
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
    ]


@pytest.mark.parametrize("protocol", ["2025-06-18", "2025-03-26", "2024-11-05"])
def test_each_protocol_version_it_speaks_is_accepted_and_recorded(protocol: str) -> None:
    info = client(answer(1, hello(protocol)))[0].initialize()
    assert info.protocol_version == protocol


@pytest.mark.parametrize("protocol", ["2023-01-01", "", None, 5, "2025-06-18 "])
def test_a_protocol_it_does_not_speak_is_refused_before_it_says_initialized(protocol: Any) -> None:
    mcp, wire = client(answer(1, hello(protocol)))
    message = refused(mcp.initialize, "MCP_PROTOCOL_UNSUPPORTED")
    assert "this client speaks 2025-06-18, 2025-03-26, 2024-11-05" in message
    assert len(wire.sent) == 1


@pytest.mark.parametrize(
    "server",
    [
        None,
        "files",
        [],
        {},
        {"name": "x"},
        {"version": "1"},
        {"name": "", "version": "1"},
        {"name": "x", "version": 2},
    ],
)
def test_a_server_that_does_not_say_who_it_is_is_refused(server: Any) -> None:
    mcp, wire = client(answer(1, hello(serverInfo=server)))
    refused(mcp.initialize, "MCP_REPLY_INVALID")
    assert len(wire.sent) == 1


# ------------------------------------------------------------------------------ list_tools
TOOL = {"name": "read", "description": "Reads a file.", "inputSchema": {"type": "object"}}


def test_a_single_page_of_tools_becomes_a_tool_set() -> None:
    mcp, wire = client(answer(1, {"tools": [TOOL, {**TOOL, "name": "write"}]}))
    tools = mcp.list_tools()
    assert isinstance(tools, McpToolSet) and tools.names() == ("read", "write")
    assert wire.sent == [{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}]


def test_pages_are_followed_with_the_cursor_until_there_is_none() -> None:
    mcp, wire = client(
        answer(1, {"tools": [TOOL], "nextCursor": "page2"}),
        answer(2, {"tools": [{**TOOL, "name": "write"}]}),
    )
    assert mcp.list_tools().names() == ("read", "write")
    assert [m["params"] for m in wire.sent] == [{}, {"cursor": "page2"}]


def test_a_missing_description_is_empty_text() -> None:
    entry = {"name": "read", "inputSchema": {"type": "object"}}
    tools = client(answer(1, {"tools": [entry]}))[0].list_tools()
    assert tools.tools[0].description == ""


@pytest.mark.parametrize(
    "tools",
    [
        None,
        "x",
        {"a": 1},
        ["not an object"],
        [{"description": "no name", "inputSchema": {"type": "object"}}],
        [{"name": 5, "inputSchema": {"type": "object"}}],
        [{"name": "", "inputSchema": {"type": "object"}}],
        [{"name": "x"}],
        [{"name": "x", "inputSchema": "no"}],
        [{"name": "x", "inputSchema": {"type": "object"}, "description": 5}],
        [TOOL, TOOL],
    ],
)
def test_a_tool_list_that_is_not_what_it_should_be_is_refused_whole(tools: Any) -> None:
    refused(client(answer(1, {"tools": tools}))[0].list_tools, "MCP_REPLY_INVALID")


def test_a_cursor_that_is_not_text_is_refused() -> None:
    refused(
        client(answer(1, {"tools": [TOOL], "nextCursor": 5}))[0].list_tools, "MCP_REPLY_INVALID"
    )


def test_exactly_500_tools_are_allowed_and_501_are_not() -> None:
    many = [{**TOOL, "name": f"t{n}"} for n in range(501)]
    assert len(client(answer(1, {"tools": many[:500]}))[0].list_tools().tools) == 500
    message = refused(client(answer(1, {"tools": many}))[0].list_tools, "MCP_REPLY_INVALID")
    assert "more than 500 tools" in message


def test_the_tool_count_is_checked_across_pages() -> None:
    page = lambda n, start: answer(
        n,
        {
            "tools": [{**TOOL, "name": f"t{i}"} for i in range(start, start + 300)],
            "nextCursor": "c",
        },
    )
    refused(client(page(1, 0), page(2, 300))[0].list_tools, "MCP_REPLY_INVALID")


def test_a_tool_name_repeated_across_pages_is_refused() -> None:
    mcp, _ = client(answer(1, {"tools": [TOOL], "nextCursor": "c"}), answer(2, {"tools": [TOOL]}))
    refused(mcp.list_tools, "MCP_REPLY_INVALID")


def test_twenty_pages_are_followed_and_a_twenty_first_is_not() -> None:
    def pages(count: int, last: bool) -> list[dict[str, Any]]:
        out = [
            answer(n, {"tools": [{**TOOL, "name": f"t{n}"}], "nextCursor": "c"})
            for n in range(1, count)
        ]
        tail = {"tools": [{**TOOL, "name": f"t{count}"}]}
        return [*out, answer(count, tail if last else {**tail, "nextCursor": "c"})]

    assert len(client(*pages(20, True))[0].list_tools().tools) == 20
    message = refused(client(*pages(20, False))[0].list_tools, "MCP_REPLY_INVALID")
    assert "past 20 pages" in message


# ------------------------------------------------------------------------------- call_tool
def text(value: str) -> dict[str, Any]:
    return {"type": "text", "text": value}


def test_a_call_sends_the_name_and_a_copy_of_the_arguments_and_returns_the_text() -> None:
    mcp, wire = client(answer(1, {"content": [text("one"), text("two")]}))
    arguments = {"path": "/x"}
    result = mcp.call_tool("read", arguments)
    assert (result.text, result.is_error) == ("one\ntwo", False)
    assert wire.sent[0]["method"] == "tools/call"
    assert wire.sent[0]["params"] == {"name": "read", "arguments": {"path": "/x"}}
    assert wire.sent[0]["params"]["arguments"] is not arguments


def test_anything_that_is_not_text_is_noted_as_left_out_and_not_passed_on() -> None:
    blocks = [
        text("kept"),
        {"type": "image", "data": "AAAA", "mimeType": "image/png"},
        {"type": "resource_link", "uri": "file:///etc/passwd"},
        {"type": "IMG<script>!", "x": 1},
        {"type": 5},
        {"no": "type"},
        "a bare string",
        {"type": "text", "text": 5},
    ]
    result = client(answer(1, {"content": blocks}))[0].call_tool("t", {})
    assert result.text.split("\n") == [
        "kept",
        "[image content omitted]",
        "[resource_link content omitted]",
        "[unknown content omitted]",
        "[unknown content omitted]",
        "[unknown content omitted]",
        "[unknown content omitted]",
        "[text content omitted]",
    ]
    assert "passwd" not in result.text and "AAAA" not in result.text


def test_a_type_name_of_twenty_lowercase_letters_is_shown_and_longer_is_not() -> None:
    result = client(answer(1, {"content": [{"type": "a" * 20}, {"type": "a" * 21}]}))[0].call_tool(
        "t", {}
    )
    assert result.text == f"[{'a' * 20} content omitted]\n[unknown content omitted]"


def test_the_error_flag_is_true_when_the_server_says_true() -> None:
    assert client(answer(1, {"content": [], "isError": True}))[0].call_tool("t", {}).is_error


@pytest.mark.parametrize("flag", [False, None, "true", 1, "yes"])
def test_anything_else_is_not_an_error(flag: Any) -> None:
    assert not client(answer(1, {"content": [], "isError": flag}))[0].call_tool("t", {}).is_error


def test_no_content_gives_empty_text_unless_there_is_structured_content() -> None:
    assert client(answer(1, {}))[0].call_tool("t", {}).text == ""
    assert client(answer(1, {"content": []}))[0].call_tool("t", {}).text == ""
    structured = answer(1, {"content": [], "structuredContent": {"b": 1, "a": [2]}})
    assert client(structured)[0].call_tool("t", {}).text == '{"a": [2], "b": 1}'
    as_list = answer(1, {"structuredContent": [1, 2]})
    assert client(as_list)[0].call_tool("t", {}).text == "[1, 2]"
    ignored = answer(1, {"structuredContent": "just text"})
    assert client(ignored)[0].call_tool("t", {}).text == ""


def test_structured_content_is_not_added_when_there_is_text() -> None:
    result = client(answer(1, {"content": [text("hi")], "structuredContent": {"a": 1}}))[
        0
    ].call_tool("t", {})
    assert result.text == "hi"


def test_content_that_is_not_a_list_is_refused() -> None:
    mcp, _ = client(answer(1, {"content": "text"}))
    refused(lambda: mcp.call_tool("t", {}), "MCP_REPLY_INVALID")


# ---------------------------------------------------------------------------------- errors
def test_a_json_rpc_error_is_the_servers_failure_with_its_message_quoted() -> None:
    message = refused(
        lambda: client(fail(1, "no such file"))[0].call_tool("t", {}), "MCP_SERVER_ERROR"
    )
    assert message == "tools/call failed: 'no such file'"


def test_a_long_error_message_is_cut_to_200_characters() -> None:
    message = refused(lambda: client(fail(1, "x" * 500))[0].call_tool("t", {}), "MCP_SERVER_ERROR")
    assert message == f"tools/call failed: {'x' * 200!r}"


def test_an_error_that_is_not_an_object_is_still_reported() -> None:
    reply = {"jsonrpc": "2.0", "id": 1, "error": "plain text"}
    message = refused(lambda: client(reply)[0].call_tool("t", {}), "MCP_SERVER_ERROR")
    assert message == "tools/call failed: 'plain text'"


@pytest.mark.parametrize(
    "reply", [{"jsonrpc": "2.0", "id": 1}, answer(1, None), answer(1, "x"), answer(1, [1])]
)
def test_an_answer_with_no_result_object_is_refused(reply: dict[str, Any]) -> None:
    refused(lambda: client(reply)[0].call_tool("t", {}), "MCP_REPLY_INVALID")


# ------------------------------------------------------------- what the server may ask of us
def test_a_ping_from_the_server_is_answered_and_the_wait_goes_on() -> None:
    mcp, wire = client(
        {"jsonrpc": "2.0", "id": "p1", "method": "ping"}, answer(1, {"content": [text("ok")]})
    )
    assert mcp.call_tool("t", {}).text == "ok"
    assert wire.sent[1] == {"jsonrpc": "2.0", "id": "p1", "result": {}}


@pytest.mark.parametrize(
    "method", ["sampling/createMessage", "roots/list", "elicitation/create", "anything/else"]
)
def test_every_other_request_from_the_server_is_refused_so_it_cannot_drive_the_model(
    method: str,
) -> None:
    request = {"jsonrpc": "2.0", "id": 77, "method": method, "params": {"messages": ["do it"]}}
    mcp, wire = client(request, answer(1, {"content": []}))
    mcp.call_tool("t", {})
    assert wire.sent[1] == {
        "jsonrpc": "2.0",
        "id": 77,
        "error": {"code": -32601, "message": "method not found"},
    }


def test_a_notification_from_the_server_is_ignored_and_not_answered() -> None:
    mcp, wire = client(
        {"jsonrpc": "2.0", "method": "notifications/progress"}, answer(1, {"content": []})
    )
    mcp.call_tool("t", {})
    assert len(wire.sent) == 1


def test_an_answer_to_some_other_request_is_ignored() -> None:
    mcp, _ = client(
        answer(99, {"content": [text("stale")]}), answer(1, {"content": [text("mine")]})
    )
    assert mcp.call_tool("t", {}).text == "mine"


def test_a_hundred_unrelated_messages_are_tolerated_and_a_hundred_and_one_are_not() -> None:
    noise = {"jsonrpc": "2.0", "method": "notifications/message"}
    assert client(*([noise] * 100), answer(1, {"content": []}))[0].call_tool("t", {}).text == ""
    mcp, wire = client(*([noise] * 101))
    message = refused(lambda: mcp.call_tool("t", {}), "MCP_REPLY_INVALID")
    assert "more than 100 messages" in message
    assert wire.incoming == []


# -------------------------------------------------------------------------- the conversation
def test_request_ids_count_up_across_requests() -> None:
    mcp, wire = client(answer(1, hello()), answer(2, {"tools": []}), answer(3, {"content": []}))
    mcp.initialize()
    mcp.list_tools()
    mcp.call_tool("t", {})
    assert [m["id"] for m in wire.sent if "id" in m] == [1, 2, 3]


def test_every_wait_uses_the_configured_timeout_and_close_reaches_the_transport() -> None:
    mcp, wire = client(answer(1, {"content": []}), timeout=4.5)
    mcp.call_tool("t", {})
    mcp.close()
    assert wire.timeouts == [4.5] and wire.closed == 1


@pytest.mark.parametrize("timeout", [0, -1, 0.0])
def test_a_timeout_is_more_than_zero(timeout: float) -> None:
    with pytest.raises(ValueError, match="more than zero"):
        McpClient(Wire(), "n", "v", timeout)


def test_a_transport_that_times_out_or_is_gone_is_not_hidden() -> None:
    mcp, _ = client(TransientStageError("no answer"))
    with pytest.raises(TransientStageError, match="no answer"):
        mcp.call_tool("t", {})
    gone = ApplicationError(code="MCP_SERVER_CLOSED", message="the server exited", http_status=502)
    with pytest.raises(ApplicationError) as error:
        client(gone)[0].call_tool("t", {})
    assert error.value is gone


def test_a_block_that_is_not_text_cannot_smuggle_text_in_a_text_field() -> None:
    blocks = [{"type": "image", "text": "smuggled instructions"}, {"type": "resource", "text": "x"}]
    result = client(answer(1, {"content": blocks}))[0].call_tool("t", {})
    assert result.text == "[image content omitted]\n[resource content omitted]"
