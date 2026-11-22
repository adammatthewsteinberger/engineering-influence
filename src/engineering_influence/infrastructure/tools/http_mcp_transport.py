# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Talks to a remote MCP server over Streamable HTTP, one POST per message."""

import contextlib
import json
import re
import time
from collections import deque
from collections.abc import Callable, Iterator, Mapping
from typing import Any
from urllib.parse import urlsplit

import httpx

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.tools.sse_event_reader import SseEventReader
from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface
from engineering_influence.interfaces.outbound_url_policy_interface import (
    OutboundUrlPolicyInterface,
)


class HttpMcpTransport(McpTransportInterface):
    """The Streamable HTTP transport of MCP, with the rules a pinned server is held to.

    - **Where it goes** is the injected URL policy's decision, asked before every request (so a
      name that now resolves somewhere inward is refused), and **a redirect is never followed**: a
      3xx is an error. A server cannot send this client, or its credential, anywhere else.
    - **What it sends** is the JSON-RPC message, a generic user agent, no cookies (any a server sets
      are dropped after each exchange) and, when the lock names a variable for it, one
      ``Authorization: Bearer`` header. The credential goes to the locked address and nowhere else,
      and is never written into an error message, which names the host alone.
    - **What it reads** is bounded on every side: a reply of at most ``max_reply_bytes``, in plain
      JSON or as server-sent events, uncompressed, within ``request_seconds`` from the first byte
      sent, with at most ``MAX_MESSAGES`` messages per request. A session lives ``session_seconds``;
      after that every request fails and the session is not started again, as with a local server.
    - **A request is answered inside its own POST.** A reply that arrives as a stream is read until
      the answer to this request has come (or the stream ends), and every message read is queued for
      ``receive``, in order. No separate stream is opened for messages the server starts, so a
      server that wants to talk first has nothing to talk to; what it asks within a reply is
      answered or refused by the client above, as with a local server.
    - **The session** is the server's ``Mcp-Session-Id``, kept from the first reply and sent back, and
      the protocol version the server agreed in its answer to ``initialize``, which is sent on every
      later request. Closing the transport ends the session politely (a DELETE, whose failure is
      ignored) and closes the client.

    The name is resolved when the policy is asked and again when the connection is made, so a
    hostile DNS server could answer differently the second time; see ``docs/THREAT_MODEL.md``.
    """

    USER_AGENT = "engineering-influence-mcp-client"
    MAX_MESSAGES = 128
    RETRYABLE = frozenset({408, 425, 429})
    VERSION = re.compile(r"\d{4}-\d{2}-\d{2}")
    SESSION = re.compile(r"[\x21-\x7e]{1,256}")

    def __init__(
        self,
        client: httpx.Client,
        url: str,
        policy: OutboundUrlPolicyInterface,
        bearer: str | None = None,
        max_reply_bytes: int = 4 * 1024 * 1024,
        request_seconds: float = 30.0,
        session_seconds: float = 4 * 3600.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if max_reply_bytes < 1 or request_seconds <= 0 or session_seconds <= 0:
            raise ValueError("a reply, a request and a session each get some room")
        self._client = client
        self._url = url
        self._host = urlsplit(url).hostname or "the host"
        self._policy = policy
        self._bearer = bearer
        self._max_bytes = max_reply_bytes
        self._request_seconds = request_seconds
        self._session_seconds = session_seconds
        self._clock = clock
        self._started = clock()
        self._pending: deque[Mapping[str, Any]] = deque()
        self._session: str | None = None
        self._protocol: str | None = None
        self._initialize_id: Any = None
        self._closed = False

    def send(self, message: Mapping[str, Any]) -> None:
        """POST one message and read the reply to it, queueing what the server answers."""
        if self._closed:
            raise self._error("MCP_SERVER_GONE", f"the session with {self._host} is closed")
        if self._clock() - self._started > self._session_seconds:
            raise self._error(
                "MCP_SESSION_EXPIRED",
                f"the session with {self._host} passed its {self._session_seconds:g} second limit",
            )
        if message.get("method") == "initialize":
            self._initialize_id = message.get("id")
        wants = message.get("id") if "method" in message else None
        body = json.dumps(dict(message), separators=(",", ":")).encode("utf-8")
        deadline = self._clock() + self._request_seconds
        with self._exchange("POST", body) as response:
            self._check(response)
            self._remember_session(response)
            if response.status_code != 202:
                self._read(response, wants, deadline)

    def receive(self, timeout_seconds: float) -> Mapping[str, Any]:
        """The next queued message. Nothing arrives later, because every answer came with its request."""
        if self._pending:
            return self._pending.popleft()
        raise self._error("MCP_NO_REPLY", f"{self._host} answered without a message")

    def close(self) -> None:
        """End the session if it has one, and close the client. Safe to call twice."""
        if self._closed:
            return
        self._closed = True
        try:
            if self._session is not None:
                with (
                    contextlib.suppress(ApplicationError, TransientStageError),
                    self._exchange("DELETE", None),
                ):
                    pass
        finally:
            self._client.close()

    @contextlib.contextmanager
    def _exchange(self, method: str, body: bytes | None) -> Iterator[httpx.Response]:
        verdict = self._policy.check(self._url)
        if not verdict.accepted:
            raise self._error("MCP_URL_REFUSED", f"{self._host} refused: {verdict.reason}", 503)
        try:
            with self._client.stream(
                method,
                self._url,
                headers=self._headers(body is not None),
                content=body,
                follow_redirects=False,
            ) as response:
                yield response
        except httpx.TransportError as error:
            raise TransientStageError(
                f"{self._host} could not be reached: {type(error).__name__}"
            ) from error
        finally:
            self._client.cookies.clear()

    def _headers(self, has_body: bool) -> dict[str, str]:
        headers = {
            "user-agent": self.USER_AGENT,
            "accept": "application/json, text/event-stream",
            "accept-encoding": "identity",
        }
        if has_body:
            headers["content-type"] = "application/json"
        if self._protocol is not None:
            headers["mcp-protocol-version"] = self._protocol
        if self._session is not None:
            headers["mcp-session-id"] = self._session
        if self._bearer is not None:
            headers["authorization"] = f"Bearer {self._bearer}"
        return headers

    def _check(self, response: httpx.Response) -> None:
        status = response.status_code
        if status in (200, 202):
            return
        if 300 <= status < 400:
            raise self._error(
                "MCP_REDIRECT_REFUSED",
                f"{self._host} answered with a redirect, which is not followed",
            )
        if status in (401, 403):
            raise self._error(
                "MCP_AUTH_REFUSED", f"{self._host} refused the credentials ({status})"
            )
        if status == 404 and self._session is not None:
            raise self._error("MCP_SESSION_ENDED", f"{self._host} no longer knows this session")
        if status in self.RETRYABLE or status >= 500:
            raise TransientStageError(f"{self._host} answered {status}")
        raise self._error("MCP_HTTP_ERROR", f"{self._host} answered {status}")

    def _remember_session(self, response: httpx.Response) -> None:
        given = response.headers.get("mcp-session-id")
        if given is None or self._session is not None:
            return
        if not self.SESSION.fullmatch(given):
            raise self._invalid("its session id is not visible text")
        self._session = given

    def _read(self, response: httpx.Response, wants: Any, deadline: float) -> None:
        kind = response.headers.get("content-type", "").split(";")[0].strip().lower()
        encoding = response.headers.get("content-encoding", "identity").strip().lower()
        if encoding not in ("", "identity"):
            raise self._invalid(
                f"it sent a {encoding[:20]!r} body; only uncompressed replies are read"
            )
        declared = response.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > self._max_bytes:
            raise self._invalid(f"its reply is longer than {self._max_bytes} bytes")
        if kind == "application/json":
            self._accept(self._parse(self._whole(response, deadline)))
        elif kind == "text/event-stream":
            self._stream(response, wants, deadline)
        else:
            raise self._invalid(f"it sent {kind[:40] or 'no content type'}, not JSON or events")

    def _whole(self, response: httpx.Response, deadline: float) -> bytes:
        body = bytearray()
        for chunk in self._chunks(response, deadline):
            body.extend(chunk)
        return bytes(body)

    def _stream(self, response: httpx.Response, wants: Any, deadline: float) -> None:
        reader = SseEventReader(self._max_bytes)
        for chunk in self._chunks(response, deadline):
            try:
                events = reader.feed(chunk)
            except ValueError as error:
                raise self._invalid(f"its event stream is not usable: {error}") from error
            for data in events:
                message = self._parse(data.encode("utf-8"))
                self._accept(message)
                if wants is not None and "method" not in message and message.get("id") == wants:
                    return

    def _chunks(self, response: httpx.Response, deadline: float) -> Iterator[bytes]:
        total = 0
        for chunk in response.iter_bytes():
            total += len(chunk)
            if total > self._max_bytes:
                raise self._invalid(f"its reply is longer than {self._max_bytes} bytes")
            if self._clock() > deadline:
                raise TransientStageError(
                    f"{self._host} did not finish answering in {self._request_seconds:g} seconds"
                )
            yield chunk

    def _parse(self, data: bytes) -> Mapping[str, Any]:
        try:
            message = json.loads(data)
        except (ValueError, RecursionError) as error:
            raise self._invalid("a message is not JSON") from error
        if not isinstance(message, dict):
            raise self._invalid("a message is not a JSON object (batches are not accepted)")
        return message

    def _accept(self, message: Mapping[str, Any]) -> None:
        if len(self._pending) >= self.MAX_MESSAGES:
            raise self._invalid(f"it sent more than {self.MAX_MESSAGES} messages in one reply")
        if (
            self._initialize_id is not None
            and "method" not in message
            and message.get("id") == self._initialize_id
        ):
            self._initialize_id = None
            self._note_protocol(message.get("result"))
        self._pending.append(message)

    def _note_protocol(self, result: Any) -> None:
        version = result.get("protocolVersion") if isinstance(result, Mapping) else None
        if isinstance(version, str) and self.VERSION.fullmatch(version):
            self._protocol = version

    def _invalid(self, why: str) -> ApplicationError:
        return self._error(
            "MCP_REPLY_INVALID", f"{self._host} sent a reply this client cannot use: {why}"
        )

    @staticmethod
    def _error(code: str, message: str, status: int = 502) -> ApplicationError:
        return ApplicationError(code=code, message=message, http_status=status)
