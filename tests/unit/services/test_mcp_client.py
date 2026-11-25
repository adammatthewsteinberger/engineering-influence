# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""McpClient: the protocol it speaks, what it refuses to offer, and what it does with a hostile server."""

from collections.abc import Mapping
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface
from engineering_influence.models.mcp_call_result import McpCallResult
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


# ------------------------------------------------------------------------------- resources
def resourceful(*incoming: Any, capabilities: Any = None) -> tuple[McpClient, Wire]:
    """A client that has initialized against a server declaring ``capabilities`` (resources by default)."""
    declared = {"resources": {}} if capabilities is None else capabilities
    return client(answer(1, hello(capabilities=declared)), *incoming)


def listed(mcp: McpClient, wire: Wire, tools: list[Any] | None = None) -> McpToolSet:
    mcp.initialize()
    wire.incoming.insert(0, answer(2, {"tools": [TOOL] if tools is None else tools}))
    return mcp.list_tools()


def read_text(value: str) -> dict[str, Any]:
    return {"contents": [{"uri": "x://a", "text": value}]}


def test_a_server_that_declares_resources_gets_two_fixed_tools_after_its_own() -> None:
    mcp, wire = resourceful()
    tools = listed(mcp, wire)
    assert tools.names() == ("list_resources", "read", "read_resource")  # names() is sorted
    assert [tool.name for tool in tools.tools] == ["read", "list_resources", "read_resource"]
    by_name = {tool.name: tool for tool in tools.tools}
    listing, reading = by_name["list_resources"], by_name["read_resource"]
    assert listing.input_schema == {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }
    assert reading.input_schema["required"] == ["uri"]
    assert reading.input_schema["properties"]["uri"] == {"type": "string", "maxLength": 2000}
    assert "uri" in listing.description and "list_resources" in reading.description
    assert all(tool.offerable("files") for tool in (listing, reading))


@pytest.mark.parametrize(
    "capabilities",
    [
        {},
        {"tools": {}},
        {"resources": True},
        {"resources": None},
        {"resources": ["x"]},
        "resources",
        ["resources"],
    ],
)
def test_a_server_that_does_not_declare_resources_gets_no_resource_tool(capabilities: Any) -> None:
    mcp, wire = resourceful(capabilities=capabilities)
    assert listed(mcp, wire).names() == ("read",)


def test_a_server_that_sent_no_capabilities_at_all_gets_none() -> None:
    mcp, wire = client(answer(1, hello()))
    assert listed(mcp, wire).names() == ("read",)


@pytest.mark.parametrize("taken", ["list_resources", "read_resource"])
def test_a_server_with_a_tool_of_a_reserved_name_gets_neither_and_that_tool_is_called_as_a_tool(
    taken: str,
) -> None:
    mcp, wire = resourceful()
    tools = listed(mcp, wire, [{**TOOL, "name": taken}])
    assert tools.names() == (taken,)
    wire.incoming.append(answer(3, {"content": [text("its own answer")]}))
    assert mcp.call_tool(taken, {"uri": "x://a"}).text == "its own answer"
    assert wire.sent[-1]["method"] == "tools/call"


def test_the_resource_tools_are_part_of_the_hash_so_a_server_that_stops_declaring_them_changes_it() -> (
    None
):
    with_resources = listed(*resourceful())
    without = listed(*resourceful(capabilities={}))
    assert with_resources.digest() != without.digest()
    again = listed(*resourceful())
    assert again.digest() == with_resources.digest()


def test_a_name_is_only_a_resource_tool_after_the_tools_were_listed_and_the_server_declared_them() -> (
    None
):
    mcp, wire = client(
        answer(1, hello(capabilities={"resources": {}})), answer(2, {"content": [text("tool")]})
    )
    mcp.initialize()
    assert mcp.call_tool("read_resource", {"uri": "x://a"}).text == "tool"
    assert wire.sent[-1]["method"] == "tools/call"


def test_a_non_resource_tool_is_still_called_as_a_tool_when_resources_are_declared() -> None:
    mcp, wire = resourceful()
    listed(mcp, wire)
    wire.incoming.append(answer(3, {"content": [text("done")]}))
    assert mcp.call_tool("read", {"path": "a"}).text == "done"
    assert wire.sent[-1] == {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {"name": "read", "arguments": {"path": "a"}},
    }


# ---- list_resources
def call_list(*pages: Any) -> tuple[McpClient, Wire]:
    mcp, wire = resourceful()
    listed(mcp, wire)
    wire.incoming.extend(pages)
    return mcp, wire


def test_listing_resources_sends_resources_list_and_gives_one_line_each() -> None:
    mcp, wire = call_list(
        answer(
            3,
            {
                "resources": [
                    {"uri": "notes://a", "name": "Notes A", "mimeType": "text/plain"},
                    {"uri": "notes://b"},
                    {"uri": "notes://c", "name": "Only a name"},
                    {"uri": "notes://d", "mimeType": "image/png"},
                ]
            },
        )
    )
    result = mcp.call_tool("list_resources", {})
    assert wire.sent[-1] == {"jsonrpc": "2.0", "id": 3, "method": "resources/list", "params": {}}
    assert (result.text, result.is_error) == (
        "notes://a - Notes A (text/plain)\nnotes://b\nnotes://c - Only a name\nnotes://d (image/png)",
        False,
    )


def test_a_name_and_type_are_made_one_line_and_cut() -> None:
    mcp, _ = call_list(
        answer(
            3,
            {
                "resources": [
                    {"uri": "x://a", "name": "Bad\x1b[31m\nname  here", "mimeType": "t" * 80},
                    {"uri": "x://b", "name": "n" * 150, "mimeType": 5},
                    {"uri": "x://c", "name": ["no"], "mimeType": None},
                ]
            },
        )
    )
    lines = mcp.call_tool("list_resources", {}).text.splitlines()
    assert lines[0] == "x://a - Bad [31m name here (" + "t" * 60 + ")"
    assert lines[1] == "x://b - " + "n" * 100
    assert lines[2] == "x://c"


def test_pages_of_resources_are_followed() -> None:
    mcp, wire = call_list(
        answer(3, {"resources": [{"uri": "x://a"}], "nextCursor": "p2"}),
        answer(4, {"resources": [{"uri": "x://b"}]}),
    )
    assert mcp.call_tool("list_resources", {}).text == "x://a\nx://b"
    assert [m["params"] for m in wire.sent[-2:]] == [{}, {"cursor": "p2"}]


def test_exactly_200_resources_are_all_shown_and_more_are_counted_not_listed() -> None:
    names = [{"uri": f"x://{n:03d}"} for n in range(200)]
    mcp, _ = call_list(answer(3, {"resources": names}))
    assert len(mcp.call_tool("list_resources", {}).text.splitlines()) == 200
    mcp, _ = call_list(answer(3, {"resources": [*names, {"uri": "x://200"}, {"uri": "x://201"}]}))
    shown = mcp.call_tool("list_resources", {}).text.splitlines()
    assert len(shown) == 201 and shown[-1] == "[2 more resources not shown]"
    assert "x://200" not in "\n".join(shown)


def test_a_server_with_no_resources_says_so() -> None:
    mcp, _ = call_list(answer(3, {"resources": []}))
    assert mcp.call_tool("list_resources", {}).text == "the server lists no resources"


@pytest.mark.parametrize(
    "page",
    [
        {"resources": "x"},
        {},
        {"resources": ["x://a"]},
        {"resources": [{}]},
        {"resources": [{"uri": ""}]},
        {"resources": [{"uri": 3}]},
        {"resources": [{"uri": "x" * 2001}]},
        {"resources": [{"uri": "a\nb"}]},
        {"resources": [{"uri": "x://a"}], "nextCursor": 7},
    ],
)
def test_a_resource_list_that_is_not_what_it_should_be_is_refused_whole(page: Any) -> None:
    mcp, _ = call_list(answer(3, page))
    with pytest.raises(ApplicationError) as error:
        mcp.call_tool("list_resources", {})
    assert error.value.code == "MCP_REPLY_INVALID"


def test_a_uri_of_exactly_2000_characters_is_listed() -> None:
    mcp, _ = call_list(answer(3, {"resources": [{"uri": "x" * 2000}]}))
    assert mcp.call_tool("list_resources", {}).text == "x" * 2000


def test_twenty_pages_of_resources_are_followed_and_a_twenty_first_is_not() -> None:
    pages = [answer(3 + n, {"resources": [], "nextCursor": f"p{n}"}) for n in range(20)]
    mcp, _ = call_list(*pages)
    with pytest.raises(ApplicationError, match="runs past 20 pages"):
        mcp.call_tool("list_resources", {})
    last = [answer(3 + n, {"resources": [], "nextCursor": f"p{n}"}) for n in range(19)]
    mcp, _ = call_list(*last, answer(22, {"resources": [{"uri": "x://z"}]}))
    assert mcp.call_tool("list_resources", {}).text == "x://z"


# ---- read_resource
def call_read(reply: Any) -> tuple[McpClient, Wire]:
    mcp, wire = resourceful()
    listed(mcp, wire)
    wire.incoming.append(reply)
    return mcp, wire


def test_reading_a_resource_sends_its_uri_and_returns_its_text() -> None:
    mcp, wire = call_read(
        answer(3, {"contents": [{"uri": "x://a", "text": "one"}, {"text": "two"}]})
    )
    result = mcp.call_tool("read_resource", {"uri": "x://a"})
    assert wire.sent[-1] == {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "resources/read",
        "params": {"uri": "x://a"},
    }
    assert (result.text, result.is_error) == ("one\ntwo", False)


def test_a_binary_resource_is_noted_as_left_out_and_never_passed_on() -> None:
    mcp, _ = call_read(
        answer(
            3,
            {
                "contents": [
                    {"uri": "x://a", "blob": "iVBORw0KGgo="},
                    "plain string",
                    {"uri": "x://b", "text": 5},
                    {"text": "kept"},
                ]
            },
        )
    )
    text_ = mcp.call_tool("read_resource", {"uri": "x://a"}).text
    assert (
        text_
        == "[binary content omitted]\n[binary content omitted]\n[binary content omitted]\nkept"
    )
    assert "iVBOR" not in text_


def test_a_resource_with_no_contents_reads_as_empty_text() -> None:
    mcp, _ = call_read(answer(3, {"contents": []}))
    assert mcp.call_tool("read_resource", {"uri": "x://a"}) == McpCallResult("", False)


@pytest.mark.parametrize("reply", [{"contents": "x"}, {}, {"contents": {"text": "x"}}])
def test_contents_that_are_not_a_list_are_refused(reply: Any) -> None:
    mcp, _ = call_read(answer(3, reply))
    with pytest.raises(ApplicationError) as error:
        mcp.call_tool("read_resource", {"uri": "x://a"})
    assert error.value.code == "MCP_REPLY_INVALID"


@pytest.mark.parametrize(
    "uri", [None, "", 3, ["x://a"], "x" * 2001, "x://a\nsecond", "x://\x1b[0m"]
)
def test_a_uri_that_is_not_one_line_of_text_is_a_failed_call_and_nothing_is_sent(uri: Any) -> None:
    mcp, wire = resourceful()
    listed(mcp, wire)
    sent = len(wire.sent)
    result = mcp.call_tool("read_resource", {"uri": uri})
    assert result.is_error and "one line of text" in result.text
    assert len(wire.sent) == sent


def test_a_missing_uri_argument_is_a_failed_call_too() -> None:
    mcp, wire = resourceful()
    listed(mcp, wire)
    assert mcp.call_tool("read_resource", {}).is_error


def test_a_uri_of_exactly_2000_characters_is_sent() -> None:
    mcp, wire = call_read(answer(3, read_text("ok")))
    assert mcp.call_tool("read_resource", {"uri": "x" * 2000}).text == "ok"
    assert wire.sent[-1]["params"] == {"uri": "x" * 2000}


def test_a_server_error_for_a_resource_is_the_servers_failure_with_its_message_quoted() -> None:
    mcp, _ = call_read(fail(3, "resource not found", -32002))
    with pytest.raises(ApplicationError) as error:
        mcp.call_tool("read_resource", {"uri": "x://missing"})
    assert error.value.code == "MCP_SERVER_ERROR"
    assert "resources/read failed: 'resource not found'" in error.value.message


def test_a_server_that_gains_a_tool_of_a_reserved_name_between_two_listings_loses_ours() -> None:
    mcp, wire = resourceful()
    assert listed(mcp, wire).names() == ("list_resources", "read", "read_resource")
    wire.incoming.extend(
        [
            answer(3, {"tools": [{**TOOL, "name": "read_resource"}]}),
            answer(4, {"content": [text("the server's own")]}),
        ]
    )
    assert mcp.list_tools().names() == ("read_resource",)
    assert mcp.call_tool("read_resource", {"uri": "x://a"}).text == "the server's own"
    assert wire.sent[-1]["method"] == "tools/call"
