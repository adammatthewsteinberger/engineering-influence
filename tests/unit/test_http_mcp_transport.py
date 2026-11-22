# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""HttpMcpTransport: one POST per message, never a redirect, never past the pinner, and every reply bounded."""

import itertools
import json
from collections.abc import Callable, Iterator
from typing import Any

import httpx
import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.tools.http_mcp_transport import HttpMcpTransport
from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface
from engineering_influence.interfaces.outbound_url_pinner_interface import (
    OutboundUrlPinnerInterface,
)
from engineering_influence.models.pin_decision import PinDecision
from engineering_influence.models.pinned_target import PinnedTarget

URL = "https://mcp.example.com/v1/mcp"
PINNED = "https://93.184.216.34/v1/mcp"
TOKEN = "s3cr3t-token"
INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
LIST = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
NOTE = {"jsonrpc": "2.0", "method": "notifications/initialized"}


class Pinner(OutboundUrlPinnerInterface):
    """Pins every address to one vetted IP, and remembers each URL it was asked about."""

    def __init__(self, refuse: str | None = None) -> None:
        self.refuse = refuse
        self.checked: list[str] = []

    def pin(self, url: str) -> PinDecision:
        self.checked.append(url)
        if self.refuse:
            return PinDecision.refused(self.refuse)
        return PinDecision.pinned(PinnedTarget(PINNED, "mcp.example.com", "mcp.example.com"))


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


Handler = Callable[[httpx.Request], httpx.Response]


class Rig:
    """A transport over a scripted server, with everything the server was sent."""

    def __init__(self, handler: Handler, **options: Any) -> None:
        self.requests: list[httpx.Request] = []
        self.pinner = options.pop("pinner", None) or Pinner()
        self.clock = options.pop("clock", None) or Clock()

        def seen(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return handler(request)

        self.client = httpx.Client(transport=httpx.MockTransport(seen))
        self.transport = HttpMcpTransport(
            self.client, URL, self.pinner, options.pop("bearer", None), clock=self.clock, **options
        )

    def body(self, index: int = -1) -> Any:
        return json.loads(self.requests[index].content)


def reply(message: Any, **headers: str) -> httpx.Response:
    return httpx.Response(200, json=message, headers=headers)


def events(*messages: Any, tail: bytes = b"") -> httpx.Response:
    body = b"".join(b"data: " + json.dumps(m).encode() + b"\n\n" for m in messages) + tail
    return httpx.Response(200, content=body, headers={"content-type": "text/event-stream"})


def answer(request: httpx.Request, **result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": json.loads(request.content)["id"], "result": result}


def refused_with(code: str, run: Callable[[], Any], status: int = 502) -> ApplicationError:
    with pytest.raises(ApplicationError) as error:
        run()
    assert (error.value.code, error.value.http_status) == (code, status)
    return error.value


def test_it_is_a_transport() -> None:
    assert isinstance(Rig(lambda r: reply({})).transport, McpTransportInterface)


@pytest.mark.parametrize(
    "options", [{"max_reply_bytes": 0}, {"request_seconds": 0}, {"session_seconds": 0}]
)
def test_a_limit_with_no_room_in_it_is_refused(options: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="each get some room"):
        Rig(lambda r: reply({}), **options)


# ----------------------------------------------------------------------------- what is sent
def test_a_message_is_one_post_of_its_json_with_the_headers_a_streamable_server_expects() -> None:
    rig = Rig(lambda r: reply(answer(r)))
    rig.transport.send(INIT)
    [request] = rig.requests
    assert (request.method, str(request.url)) == ("POST", PINNED)
    assert json.loads(request.content) == INIT
    assert request.headers["content-type"] == "application/json"
    assert request.headers["accept"] == "application/json, text/event-stream"
    assert request.headers["accept-encoding"] == "identity"
    assert request.headers["user-agent"] == "engineering-influence-mcp-client"
    assert "authorization" not in request.headers and "mcp-session-id" not in request.headers
    assert "mcp-protocol-version" not in request.headers


def test_the_bearer_token_goes_with_every_request_to_the_locked_address() -> None:
    rig = Rig(lambda r: reply(answer(r)), bearer=TOKEN)
    rig.transport.send(INIT)
    rig.transport.send(LIST)
    assert [r.headers["authorization"] for r in rig.requests] == [f"Bearer {TOKEN}"] * 2
    assert {str(r.url) for r in rig.requests} == {PINNED}


def test_the_pinner_is_asked_about_the_address_before_every_request() -> None:
    rig = Rig(lambda r: reply(answer(r)))
    rig.transport.send(INIT)
    rig.transport.send(LIST)
    assert rig.pinner.checked == [URL, URL]


def test_an_address_the_pinner_refuses_is_never_contacted_and_the_reason_is_named() -> None:
    rig = Rig(lambda r: reply(answer(r)), pinner=Pinner("non_public_address"), bearer=TOKEN)
    error = refused_with("MCP_URL_REFUSED", lambda: rig.transport.send(INIT), 503)
    assert error.message == "mcp.example.com refused: non_public_address"
    assert rig.requests == [] and TOKEN not in error.message


def test_an_address_that_turns_inward_mid_session_is_refused_from_then_on() -> None:
    rig = Rig(lambda r: reply(answer(r)))
    rig.transport.send(INIT)
    rig.pinner.refuse = "non_public_address"
    refused_with("MCP_URL_REFUSED", lambda: rig.transport.send(LIST), 503)
    assert len(rig.requests) == 1


# ----------------------------------------------------------------------- what comes back
def test_a_json_reply_is_queued_and_received() -> None:
    rig = Rig(lambda r: reply(answer(r, tools=[])))
    rig.transport.send(LIST)
    assert rig.transport.receive(30.0) == {"jsonrpc": "2.0", "id": 2, "result": {"tools": []}}


def test_a_json_reply_with_a_charset_is_read() -> None:
    rig = Rig(
        lambda r: httpx.Response(
            200,
            content=b'{"jsonrpc":"2.0","id":2,"result":{}}',
            headers={"content-type": "Application/JSON; charset=utf-8"},
        )
    )
    rig.transport.send(LIST)
    assert rig.transport.receive(1.0)["id"] == 2


def test_an_accepted_message_has_no_reply_and_receiving_then_says_so() -> None:
    rig = Rig(lambda r: httpx.Response(202))
    rig.transport.send(NOTE)
    error = refused_with("MCP_NO_REPLY", lambda: rig.transport.receive(30.0))
    assert error.message == "mcp.example.com answered without a message"


def test_receiving_does_not_wait_because_nothing_arrives_later() -> None:
    rig = Rig(lambda r: reply(answer(r)))
    refused_with("MCP_NO_REPLY", lambda: rig.transport.receive(3600.0))
    assert rig.requests == []


def test_an_event_stream_reply_is_read_and_its_messages_queued_in_order() -> None:
    progress = {"jsonrpc": "2.0", "method": "notifications/progress", "params": {}}
    rig = Rig(lambda r: events(progress, answer(r, ok=True), tail=b"data: unread\n\n"))
    rig.transport.send(LIST)
    assert rig.transport.receive(1.0) == progress
    assert rig.transport.receive(1.0)["result"] == {"ok": True}
    refused_with("MCP_NO_REPLY", lambda: rig.transport.receive(1.0))


def test_reading_stops_at_the_answer_and_the_rest_of_the_stream_is_not_read() -> None:
    pulled: list[int] = []

    def stream(request: httpx.Request) -> httpx.Response:
        def chunks() -> Iterator[bytes]:
            for index, body in enumerate((answer(request, first=True), {"late": True})):
                pulled.append(index)
                yield b"data: " + json.dumps(body).encode() + b"\n\n"

        return httpx.Response(200, content=chunks(), headers={"content-type": "text/event-stream"})

    rig = Rig(stream)
    rig.transport.send(LIST)
    assert pulled == [0] and rig.transport.receive(1.0)["result"] == {"first": True}


def test_a_request_the_server_makes_with_the_same_id_is_not_taken_for_the_answer() -> None:
    ask = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
    rig = Rig(lambda r: events(ask, answer(r, real=True)))
    rig.transport.send(LIST)
    assert rig.transport.receive(1.0) == ask
    assert rig.transport.receive(1.0)["result"] == {"real": True}


def test_an_event_stream_that_ends_without_an_answer_just_ends() -> None:
    rig = Rig(lambda r: events({"jsonrpc": "2.0", "method": "notifications/message"}))
    rig.transport.send(LIST)
    assert rig.transport.receive(1.0)["method"] == "notifications/message"
    refused_with("MCP_NO_REPLY", lambda: rig.transport.receive(1.0))


def test_a_stream_split_into_small_chunks_is_the_same_stream() -> None:
    def stream(request: httpx.Request) -> httpx.Response:
        data = b"data: " + json.dumps(answer(request, ok=1)).encode() + b"\r\n\r\n"
        return httpx.Response(
            200,
            content=(data[i : i + 3] for i in range(0, len(data), 3)),
            headers={"content-type": "text/event-stream"},
        )

    rig = Rig(stream)
    rig.transport.send(LIST)
    assert rig.transport.receive(1.0)["result"] == {"ok": 1}


def test_a_message_sent_as_a_reply_to_the_server_is_posted_and_wants_no_answer() -> None:
    rig = Rig(lambda r: httpx.Response(202))
    rig.transport.send({"jsonrpc": "2.0", "id": 9, "result": {}})
    assert rig.body() == {"jsonrpc": "2.0", "id": 9, "result": {}}
    refused_with("MCP_NO_REPLY", lambda: rig.transport.receive(1.0))


def test_a_reply_to_a_notification_is_tolerated_and_queued() -> None:
    rig = Rig(lambda r: reply({"jsonrpc": "2.0", "method": "notifications/x"}))
    rig.transport.send(NOTE)
    assert rig.transport.receive(1.0)["method"] == "notifications/x"


# --------------------------------------------------------------------- session and protocol
def test_the_session_id_from_the_first_reply_is_sent_back_and_never_replaced() -> None:
    sessions = itertools.chain(["abc123"], itertools.repeat("other"))
    rig = Rig(lambda r: reply(answer(r), **{"Mcp-Session-Id": next(sessions)}))
    rig.transport.send(INIT)
    rig.transport.send(LIST)
    rig.transport.send(LIST)
    assert [r.headers.get("mcp-session-id") for r in rig.requests] == [None, "abc123", "abc123"]


def test_a_session_id_that_is_not_visible_text_is_refused() -> None:
    rig = Rig(lambda r: reply(answer(r), **{"Mcp-Session-Id": "has space"}))
    error = refused_with("MCP_REPLY_INVALID", lambda: rig.transport.send(INIT))
    assert "session id is not visible text" in error.message


def test_the_protocol_the_server_agreed_is_sent_on_every_later_request() -> None:
    rig = Rig(
        lambda r: (
            reply(answer(r, protocolVersion="2025-03-26"))
            if "id" in json.loads(r.content)
            else httpx.Response(202)
        )
    )
    rig.transport.send(INIT)
    rig.transport.send(NOTE)
    rig.transport.send(LIST)
    assert [r.headers.get("mcp-protocol-version") for r in rig.requests] == [
        None,
        "2025-03-26",
        "2025-03-26",
    ]


@pytest.mark.parametrize("version", ["latest", "2025-6-18", 20250618, None, "2025-06-18\n"])
def test_a_protocol_version_that_is_not_a_date_is_not_repeated(version: Any) -> None:
    rig = Rig(lambda r: reply(answer(r, protocolVersion=version)))
    rig.transport.send(INIT)
    rig.transport.send(LIST)
    assert "mcp-protocol-version" not in rig.requests[1].headers


def test_an_initialize_answer_without_a_result_sets_no_protocol() -> None:
    rig = Rig(lambda r: reply({"jsonrpc": "2.0", "id": 1, "error": {"code": -1, "message": "no"}}))
    rig.transport.send(INIT)
    rig.transport.send(LIST)
    assert "mcp-protocol-version" not in rig.requests[1].headers


def test_only_the_answer_to_initialize_sets_the_protocol() -> None:
    rig = Rig(
        lambda r: reply({"jsonrpc": "2.0", "id": 77, "result": {"protocolVersion": "2025-06-18"}})
    )
    rig.transport.send(INIT)
    rig.transport.send(LIST)
    assert "mcp-protocol-version" not in rig.requests[1].headers


def test_the_protocol_is_taken_from_an_event_stream_answer_too() -> None:
    rig = Rig(lambda r: events(answer(r, protocolVersion="2024-11-05")))
    rig.transport.send(INIT)
    rig.transport.send(LIST)
    assert rig.requests[1].headers["mcp-protocol-version"] == "2024-11-05"


def test_a_request_that_is_not_initialize_never_sets_the_protocol() -> None:
    rig = Rig(lambda r: reply(answer(r, protocolVersion="2025-06-18")))
    rig.transport.send(LIST)
    rig.transport.send(LIST)
    assert "mcp-protocol-version" not in rig.requests[1].headers


def test_cookies_a_server_sets_are_never_sent_back() -> None:
    rig = Rig(lambda r: reply(answer(r), **{"set-cookie": "sid=1; Path=/"}))
    rig.transport.send(INIT)
    rig.transport.send(LIST)
    assert "cookie" not in rig.requests[1].headers and len(rig.client.cookies) == 0


# ------------------------------------------------------------------------ status codes
@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_a_redirect_is_never_followed_and_the_token_goes_nowhere_else(status: int) -> None:
    rig = Rig(
        lambda r: httpx.Response(status, headers={"location": "https://evil.example/steal"}),
        bearer=TOKEN,
    )
    error = refused_with("MCP_REDIRECT_REFUSED", lambda: rig.transport.send(INIT))
    assert error.message == "mcp.example.com answered with a redirect, which is not followed"
    assert [str(r.url) for r in rig.requests] == [PINNED]


@pytest.mark.parametrize("status", [401, 403])
def test_a_refused_credential_is_named_without_the_token(status: int) -> None:
    rig = Rig(lambda r: httpx.Response(status, text=f"bad {TOKEN}"), bearer=TOKEN)
    error = refused_with("MCP_AUTH_REFUSED", lambda: rig.transport.send(INIT))
    assert error.message == f"mcp.example.com refused the credentials ({status})"
    assert TOKEN not in error.message


def test_a_404_before_a_session_exists_is_an_ordinary_http_error() -> None:
    rig = Rig(lambda r: httpx.Response(404))
    error = refused_with("MCP_HTTP_ERROR", lambda: rig.transport.send(INIT))
    assert error.message == "mcp.example.com answered 404"


def test_a_404_after_a_session_began_means_the_session_ended() -> None:
    answers = iter([reply({"jsonrpc": "2.0", "id": 1, "result": {}}, **{"mcp-session-id": "s1"})])
    rig = Rig(lambda r: next(answers, httpx.Response(404)))
    rig.transport.send(INIT)
    error = refused_with("MCP_SESSION_ENDED", lambda: rig.transport.send(LIST))
    assert error.message == "mcp.example.com no longer knows this session"


@pytest.mark.parametrize("status", [408, 425, 429, 500, 502, 503, 504])
def test_a_status_that_might_pass_is_a_transient_failure(status: int) -> None:
    rig = Rig(lambda r: httpx.Response(status))
    with pytest.raises(TransientStageError) as error:
        rig.transport.send(INIT)
    assert str(error.value) == f"mcp.example.com answered {status}"


@pytest.mark.parametrize("status", [400, 405, 406, 410, 415, 422])
def test_any_other_status_is_an_http_error(status: int) -> None:
    rig = Rig(lambda r: httpx.Response(status))
    error = refused_with("MCP_HTTP_ERROR", lambda: rig.transport.send(INIT))
    assert error.message == f"mcp.example.com answered {status}"


@pytest.mark.parametrize("failure", [httpx.ConnectError("x"), httpx.ReadTimeout("y")])
def test_a_connection_that_fails_is_transient_and_names_the_host_and_kind_only(
    failure: Exception,
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise failure

    rig = Rig(handler, bearer=TOKEN)
    with pytest.raises(TransientStageError) as error:
        rig.transport.send(INIT)
    assert str(error.value) == f"mcp.example.com could not be reached: {type(failure).__name__}"


def test_a_connection_that_drops_mid_stream_is_transient() -> None:
    def stream(request: httpx.Request) -> httpx.Response:
        def chunks() -> Iterator[bytes]:
            yield b"data: {}\n\n"
            raise httpx.ReadError("dropped")

        return httpx.Response(200, content=chunks(), headers={"content-type": "text/event-stream"})

    rig = Rig(stream)
    with pytest.raises(TransientStageError, match="could not be reached: ReadError"):
        rig.transport.send(LIST)


# ---------------------------------------------------------------------- bounds on a reply
def test_a_declared_length_over_the_cap_is_refused_before_any_of_it_is_read() -> None:
    rig = Rig(
        lambda r: httpx.Response(
            200, content=b"{}", headers={"content-type": "application/json", "content-length": "11"}
        ),
        max_reply_bytes=10,
    )
    error = refused_with("MCP_REPLY_INVALID", lambda: rig.transport.send(LIST))
    assert "longer than 10 bytes" in error.message


def test_a_json_body_over_the_cap_is_refused_whatever_it_declares() -> None:
    body = json.dumps({"x": "y" * 50}).encode()
    rig = Rig(
        lambda r: httpx.Response(
            200,
            content=(body[i : i + 7] for i in range(0, len(body), 7)),
            headers={"content-type": "application/json"},
        ),
        max_reply_bytes=40,
    )
    error = refused_with("MCP_REPLY_INVALID", lambda: rig.transport.send(LIST))
    assert "longer than 40 bytes" in error.message


def test_a_body_exactly_at_the_cap_is_read() -> None:
    body = b'{"jsonrpc":"2.0","id":2,"result":{}}'
    rig = Rig(
        lambda r: httpx.Response(200, content=body, headers={"content-type": "application/json"}),
        max_reply_bytes=len(body),
    )
    rig.transport.send(LIST)
    assert rig.transport.receive(1.0)["id"] == 2


def test_a_stream_over_the_cap_is_refused_even_if_it_never_ends() -> None:
    def endless(request: httpx.Request) -> httpx.Response:
        def chunks() -> Iterator[bytes]:
            while True:
                yield b": " + b"x" * 20 + b"\n"

        return httpx.Response(200, content=chunks(), headers={"content-type": "text/event-stream"})

    rig = Rig(endless, max_reply_bytes=100)
    error = refused_with("MCP_REPLY_INVALID", lambda: rig.transport.send(LIST))
    assert "longer than 100 bytes" in error.message


def test_a_single_event_line_longer_than_the_reply_cap_is_refused_by_the_cap() -> None:
    body = b"data: " + b"x" * 60 + b"\n\n"
    rig = Rig(
        lambda r: httpx.Response(
            200,
            content=(body[i : i + 9] for i in range(0, len(body), 9)),
            headers={"content-type": "text/event-stream"},
        ),
        max_reply_bytes=50,
    )
    error = refused_with("MCP_REPLY_INVALID", lambda: rig.transport.send(LIST))
    assert "its reply is longer than 50 bytes" in error.message


def test_an_event_that_is_not_utf8_is_refused() -> None:
    rig = Rig(
        lambda r: httpx.Response(
            200, content=b"data: \xff\n\n", headers={"content-type": "text/event-stream"}
        )
    )
    error = refused_with("MCP_REPLY_INVALID", lambda: rig.transport.send(LIST))
    assert "event stream is not usable" in error.message


def test_a_compressed_reply_is_refused() -> None:
    rig = Rig(
        lambda r: httpx.Response(
            200,
            content=b"x",
            headers={"content-type": "application/json", "content-encoding": "gzip"},
        )
    )
    error = refused_with("MCP_REPLY_INVALID", lambda: rig.transport.send(LIST))
    assert "sent a 'gzip' body; only uncompressed replies are read" in error.message


def test_an_explicit_identity_encoding_is_fine() -> None:
    rig = Rig(
        lambda r: httpx.Response(
            200,
            content=b'{"jsonrpc":"2.0","id":2,"result":{}}',
            headers={"content-type": "application/json", "content-encoding": "identity"},
        )
    )
    rig.transport.send(LIST)
    assert rig.transport.receive(1.0)["id"] == 2


@pytest.mark.parametrize("kind", ["text/html", "text/plain", "application/xml", ""])
def test_a_reply_that_is_neither_json_nor_events_is_refused(kind: str) -> None:
    rig = Rig(
        lambda r: httpx.Response(
            200, content=b"<html>", headers={"content-type": kind} if kind else {}
        )
    )
    error = refused_with("MCP_REPLY_INVALID", lambda: rig.transport.send(LIST))
    assert f"sent {kind or 'no content type'}, not JSON or events" in error.message


@pytest.mark.parametrize(
    ("body", "why"),
    [
        (b"not json", "a message is not JSON"),
        (b"[1, 2]", "not a JSON object (batches are not accepted)"),
        (b'"text"', "not a JSON object"),
        (b"[" * 100_000, "a message is not JSON"),
    ],
)
def test_a_body_that_is_not_one_json_object_is_refused(body: bytes, why: str) -> None:
    rig = Rig(
        lambda r: httpx.Response(200, content=body, headers={"content-type": "application/json"})
    )
    assert why in refused_with("MCP_REPLY_INVALID", lambda: rig.transport.send(LIST)).message


def test_an_event_whose_data_is_not_a_json_object_is_refused() -> None:
    rig = Rig(
        lambda r: httpx.Response(
            200, content=b"data: [1]\n\n", headers={"content-type": "text/event-stream"}
        )
    )
    assert (
        "not a JSON object"
        in refused_with("MCP_REPLY_INVALID", lambda: rig.transport.send(LIST)).message
    )


def test_a_reply_with_too_many_messages_is_refused() -> None:
    chatter = {"jsonrpc": "2.0", "method": "notifications/message", "params": {}}
    rig = Rig(lambda r: events(*([chatter] * (HttpMcpTransport.MAX_MESSAGES + 1))))
    error = refused_with("MCP_REPLY_INVALID", lambda: rig.transport.send(LIST))
    assert f"more than {HttpMcpTransport.MAX_MESSAGES} messages in one reply" in error.message


def test_exactly_the_most_messages_is_allowed() -> None:
    chatter = {"jsonrpc": "2.0", "method": "notifications/message", "params": {}}
    rig = Rig(lambda r: events(*([chatter] * HttpMcpTransport.MAX_MESSAGES)))
    rig.transport.send(LIST)
    assert len(rig.transport._pending) == HttpMcpTransport.MAX_MESSAGES


def test_a_reply_that_takes_longer_than_the_request_limit_is_transient() -> None:
    clock = Clock()

    def slow(request: httpx.Request) -> httpx.Response:
        def chunks() -> Iterator[bytes]:
            clock.now += 31.0
            yield b": slow\n"

        return httpx.Response(200, content=chunks(), headers={"content-type": "text/event-stream"})

    rig = Rig(slow, clock=clock, request_seconds=30.0)
    with pytest.raises(TransientStageError) as error:
        rig.transport.send(LIST)
    assert str(error.value) == "mcp.example.com did not finish answering in 30 seconds"


def test_a_reply_that_finishes_exactly_at_the_limit_is_fine() -> None:
    clock = Clock()

    def prompt(request: httpx.Request) -> httpx.Response:
        def chunks() -> Iterator[bytes]:
            clock.now += 30.0
            yield b"data: " + json.dumps(answer(request)).encode() + b"\n\n"

        return httpx.Response(200, content=chunks(), headers={"content-type": "text/event-stream"})

    rig = Rig(prompt, clock=clock, request_seconds=30.0)
    rig.transport.send(LIST)
    assert rig.transport.receive(1.0)["id"] == 2


# ------------------------------------------------------------------------ the session's life
def test_a_session_past_its_time_limit_fails_every_request_and_asks_nothing() -> None:
    clock = Clock()
    rig = Rig(lambda r: reply(answer(r)), clock=clock, session_seconds=3600.0)
    rig.transport.send(INIT)
    clock.now += 3601.0
    error = refused_with("MCP_SESSION_EXPIRED", lambda: rig.transport.send(LIST))
    assert error.message == "the session with mcp.example.com passed its 3600 second limit"
    assert len(rig.requests) == 1
    refused_with("MCP_SESSION_EXPIRED", lambda: rig.transport.send(LIST))


def test_a_session_exactly_at_its_limit_still_works() -> None:
    clock = Clock()
    rig = Rig(lambda r: reply(answer(r)), clock=clock, session_seconds=3600.0)
    clock.now += 3600.0
    rig.transport.send(LIST)
    assert len(rig.requests) == 1


def test_closing_ends_the_session_with_a_delete_and_closes_the_client() -> None:
    rig = Rig(
        lambda r: (
            reply(answer(r), **{"mcp-session-id": "s1"})
            if r.method == "POST"
            else httpx.Response(200)
        ),
        bearer=TOKEN,
    )
    rig.transport.send(INIT)
    rig.transport.close()
    delete = rig.requests[-1]
    assert (delete.method, str(delete.url)) == ("DELETE", PINNED)
    assert (
        delete.headers["mcp-session-id"] == "s1"
        and delete.headers["authorization"] == f"Bearer {TOKEN}"
    )
    assert "content-type" not in delete.headers
    assert rig.client.is_closed


def test_closing_a_session_that_never_began_sends_nothing() -> None:
    rig = Rig(lambda r: reply(answer(r)))
    rig.transport.send(INIT)
    rig.transport.close()
    assert [r.method for r in rig.requests] == ["POST"] and rig.client.is_closed


def test_closing_twice_sends_one_delete() -> None:
    rig = Rig(
        lambda r: (
            reply(answer(r), **{"mcp-session-id": "s1"})
            if r.method == "POST"
            else httpx.Response(200)
        )
    )
    rig.transport.send(INIT)
    rig.transport.close()
    rig.transport.close()
    assert [r.method for r in rig.requests] == ["POST", "DELETE"]


@pytest.mark.parametrize("status", [405, 500, 404])
def test_a_delete_the_server_will_not_have_is_ignored(status: int) -> None:
    rig = Rig(
        lambda r: (
            reply(answer(r), **{"mcp-session-id": "s1"})
            if r.method == "POST"
            else httpx.Response(status)
        )
    )
    rig.transport.send(INIT)
    rig.transport.close()
    assert rig.client.is_closed


def test_a_delete_that_cannot_be_sent_is_ignored_and_the_client_is_still_closed() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "DELETE":
            raise httpx.ConnectError("gone")
        return reply(answer(request), **{"mcp-session-id": "s1"})

    rig = Rig(handler)
    rig.transport.send(INIT)
    rig.transport.close()
    assert rig.client.is_closed


def test_a_delete_the_pinner_now_refuses_is_ignored_and_the_client_is_still_closed() -> None:
    rig = Rig(lambda r: reply(answer(r), **{"mcp-session-id": "s1"}))
    rig.transport.send(INIT)
    rig.pinner.refuse = "non_public_address"
    rig.transport.close()
    assert [r.method for r in rig.requests] == ["POST"] and rig.client.is_closed


def test_a_closed_transport_sends_nothing_more() -> None:
    rig = Rig(lambda r: reply(answer(r)))
    rig.transport.close()
    error = refused_with("MCP_SERVER_GONE", lambda: rig.transport.send(LIST))
    assert error.message == "the session with mcp.example.com is closed"
    assert rig.requests == []


def test_a_session_id_may_be_up_to_256_visible_characters_and_no_longer() -> None:
    longest = "s" * 256
    rig = Rig(lambda r: reply(answer(r), **{"Mcp-Session-Id": longest}))
    rig.transport.send(INIT)
    rig.transport.send(LIST)
    assert rig.requests[1].headers["mcp-session-id"] == longest
    too_long = Rig(lambda r: reply(answer(r), **{"Mcp-Session-Id": "s" * 257}))
    refused_with("MCP_REPLY_INVALID", lambda: too_long.transport.send(INIT))


def test_a_reply_to_the_server_is_not_treated_as_a_request_waiting_for_its_answer() -> None:
    first = {"jsonrpc": "2.0", "id": 9, "result": {"first": True}}
    second = {"jsonrpc": "2.0", "id": 9, "result": {"second": True}}
    rig = Rig(lambda r: events(first, second))
    rig.transport.send({"jsonrpc": "2.0", "id": 9, "result": {}})
    assert [rig.transport.receive(1.0)["result"] for _ in range(2)] == [
        {"first": True},
        {"second": True},
    ]


def test_a_notification_reads_the_whole_stream_even_of_messages_with_no_id() -> None:
    bare = {"jsonrpc": "2.0", "result": {}}
    rig = Rig(lambda r: events(bare, bare))
    rig.transport.send(NOTE)
    assert rig.transport.receive(1.0) == bare and rig.transport.receive(1.0) == bare


def test_a_300_is_a_redirect_too() -> None:
    rig = Rig(lambda r: httpx.Response(300))
    refused_with("MCP_REDIRECT_REFUSED", lambda: rig.transport.send(INIT))


def test_an_encoding_named_in_capitals_is_read_as_the_encoding_it_is() -> None:
    rig = Rig(
        lambda r: httpx.Response(
            200,
            content=b'{"jsonrpc":"2.0","id":2,"result":{}}',
            headers={"content-type": "application/json", "content-encoding": " IDENTITY "},
        )
    )
    rig.transport.send(LIST)
    assert rig.transport.receive(1.0)["id"] == 2


def test_a_content_type_with_a_space_before_its_parameters_is_read() -> None:
    rig = Rig(
        lambda r: httpx.Response(
            200,
            content=b'{"jsonrpc":"2.0","id":2,"result":{}}',
            headers={"content-type": "application/json ; charset=utf-8"},
        )
    )
    rig.transport.send(LIST)
    assert rig.transport.receive(1.0)["id"] == 2


def test_a_request_the_server_makes_with_the_initialize_id_does_not_set_the_protocol() -> None:
    ask = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
    rig = Rig(lambda r: events(ask, answer(r, protocolVersion="2025-03-26")))
    rig.transport.send(INIT)
    rig.transport.send(LIST)
    assert rig.requests[1].headers["mcp-protocol-version"] == "2025-03-26"


def test_a_message_with_no_id_never_sets_the_protocol_when_no_initialize_was_sent() -> None:
    rig = Rig(lambda r: reply({"jsonrpc": "2.0", "result": {"protocolVersion": "2025-06-18"}}))
    rig.transport.send(LIST)
    rig.transport.send(LIST)
    assert "mcp-protocol-version" not in rig.requests[1].headers


def test_the_protocol_is_set_by_the_answer_to_initialize_once_and_not_by_a_later_reply() -> None:
    versions = itertools.chain(["2025-06-18"], itertools.repeat("2024-11-05"))
    rig = Rig(lambda r: reply(answer(r, protocolVersion=next(versions))))
    rig.transport.send(INIT)
    rig.transport.send({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    rig.transport.send(LIST)
    assert rig.requests[2].headers["mcp-protocol-version"] == "2025-06-18"


def test_the_request_limit_given_to_the_transport_is_the_one_it_enforces() -> None:
    clock = Clock()

    def slow(request: httpx.Request) -> httpx.Response:
        def chunks() -> Iterator[bytes]:
            clock.now += 3.0
            yield b": slow\n"

        return httpx.Response(200, content=chunks(), headers={"content-type": "text/event-stream"})

    rig = Rig(slow, clock=clock, request_seconds=2.0)
    with pytest.raises(TransientStageError, match="in 2 seconds"):
        rig.transport.send(LIST)


# ------------------------------------------------------------------------ the pinned address
def test_the_request_goes_to_the_vetted_address_but_asks_for_the_name_and_verifies_it() -> None:
    rig = Rig(lambda r: reply(answer(r)))
    rig.transport.send(INIT)
    [request] = rig.requests
    assert request.url.host == "93.184.216.34" and str(request.url) == PINNED
    assert request.headers["host"] == "mcp.example.com"
    assert request.extensions["sni_hostname"] == "mcp.example.com"


def test_every_request_of_a_session_is_pinned_again_including_the_delete() -> None:
    rig = Rig(
        lambda r: (
            reply(answer(r), **{"mcp-session-id": "s1"})
            if r.method == "POST"
            else httpx.Response(200)
        )
    )
    rig.transport.send(INIT)
    rig.transport.send(LIST)
    rig.transport.close()
    assert rig.pinner.checked == [URL, URL, URL]
    assert [r.url.host for r in rig.requests] == ["93.184.216.34"] * 3
    assert all(r.headers["host"] == "mcp.example.com" for r in rig.requests)


def test_the_original_name_never_reaches_the_client_as_the_place_to_connect() -> None:
    rig = Rig(lambda r: reply(answer(r)))
    rig.transport.send(INIT)
    assert "mcp.example.com" not in str(rig.requests[0].url)
