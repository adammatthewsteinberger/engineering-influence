# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""HttpMcpTransportFactory: the address and the credential are checked before a client is even built."""

from collections.abc import Iterator
from typing import Any

import httpx
import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.tools.http_mcp_transport_factory import (
    HttpMcpTransportFactory,
)
from engineering_influence.interfaces.mcp_remote_transport_factory_interface import (
    McpRemoteTransportFactoryInterface,
)
from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface
from engineering_influence.interfaces.outbound_url_pinner_interface import (
    OutboundUrlPinnerInterface,
)
from engineering_influence.models.pin_decision import PinDecision
from engineering_influence.models.pinned_target import PinnedTarget

URL = "https://mcp.example.com/mcp"
TOKEN = "s3cr3t-token"
INIT = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}


class Pinner(OutboundUrlPinnerInterface):
    def __init__(self, refuse: str | None = None) -> None:
        self.refuse = refuse

    def pin(self, url: str) -> PinDecision:
        if self.refuse:
            return PinDecision.refused(self.refuse)
        return PinDecision.pinned(PinnedTarget("https://93.184.216.34/mcp", "mcp.example.com"))


class Clock:
    now = 5.0

    def __call__(self) -> float:
        return self.now


class Clients:
    """Builds clients over a scripted server and remembers each one and what it was sent."""

    def __init__(self) -> None:
        self.made: list[httpx.Client] = []
        self.requests: list[httpx.Request] = []

    def __call__(self) -> httpx.Client:
        def handler(request: httpx.Request) -> httpx.Response:
            self.requests.append(request)
            return httpx.Response(200, json={"jsonrpc": "2.0", "id": 1, "result": {}})

        client = httpx.Client(transport=httpx.MockTransport(handler))
        self.made.append(client)
        return client


def factory(
    clients: Clients | None = None,
    environ: dict[str, str] | None = None,
    pinner: Pinner | None = None,
    **options: Any,
) -> tuple[HttpMcpTransportFactory, Clients]:
    made = clients or Clients()
    return (
        HttpMcpTransportFactory(
            made, pinner or Pinner(), {} if environ is None else environ, **options
        ),
        made,
    )


def refused(code: str, run: Any) -> ApplicationError:
    with pytest.raises(ApplicationError) as error:
        run()
    assert (error.value.code, error.value.http_status) == (code, 422)
    return error.value


def test_it_is_a_remote_transport_factory() -> None:
    assert isinstance(factory()[0], McpRemoteTransportFactoryInterface)


def test_a_transport_is_made_over_a_client_of_its_own_and_closing_it_closes_the_client() -> None:
    opener, clients = factory()
    first, second = opener.open(URL, ""), opener.open(URL, "")
    assert isinstance(first, McpTransportInterface) and len(clients.made) == 2
    first.close()
    assert clients.made[0].is_closed and not clients.made[1].is_closed
    second.close()


def test_no_bearer_variable_means_no_authorization_header() -> None:
    opener, clients = factory(environ={"DOCS_TOKEN": TOKEN})
    opener.open(URL, "").send(INIT)
    assert "authorization" not in clients.requests[0].headers


def test_the_named_variable_is_read_now_and_sent_as_a_bearer_token() -> None:
    environ = {"DOCS_TOKEN": TOKEN}
    opener, clients = factory(environ=environ)
    transport = opener.open(URL, "DOCS_TOKEN")
    environ["DOCS_TOKEN"] = "changed-later"
    transport.send(INIT)
    assert clients.requests[0].headers["authorization"] == f"Bearer {TOKEN}"


@pytest.mark.parametrize("environ", [{}, {"DOCS_TOKEN": ""}])
def test_a_variable_that_is_not_set_refuses_the_server_before_a_client_is_built(
    environ: dict[str, str],
) -> None:
    opener, clients = factory(environ=environ)
    error = refused("TOOL_ENV_MISSING", lambda: opener.open(URL, "DOCS_TOKEN"))
    assert error.message == "the environment variable DOCS_TOKEN is not set"
    assert clients.made == []


@pytest.mark.parametrize("value", ["has space", "tab\there", "new\nline", "café", "a" + chr(127)])
def test_a_value_that_is_not_a_bearer_token_is_refused_without_repeating_it(value: str) -> None:
    opener, clients = factory(environ={"DOCS_TOKEN": value})
    error = refused("TOOL_ENV_INVALID", lambda: opener.open(URL, "DOCS_TOKEN"))
    assert error.message == "DOCS_TOKEN is not a bearer token: printable characters, no spaces"
    assert clients.made == []


@pytest.mark.parametrize(
    "url",
    [
        "http://mcp.example.com/mcp",
        "https://user:pw@mcp.example.com/mcp",
        "https://mcp.example.com/mcp?k=v",
        "https:///mcp",
        "",
        None,
    ],
)
def test_an_address_that_is_not_allowed_is_refused_before_a_client_is_built_or_a_variable_read(
    url: Any,
) -> None:
    opener, clients = factory(environ={})
    refused("TOOL_URL_REFUSED", lambda: opener.open(url, "DOCS_TOKEN"))
    assert clients.made == []


def test_the_pinner_given_to_the_factory_governs_every_transport_it_makes() -> None:
    opener, clients = factory(pinner=Pinner("non_public_address"))
    transport = opener.open(URL, "")
    with pytest.raises(ApplicationError) as error:
        transport.send(INIT)
    assert error.value.code == "MCP_URL_REFUSED" and clients.requests == []


def test_the_session_and_request_limits_and_the_clock_reach_the_transport() -> None:
    clock = Clock()
    opener, _ = factory(session_seconds=10.0, request_seconds=2.0, clock=clock)
    transport = opener.open(URL, "")
    clock.now += 11.0
    with pytest.raises(ApplicationError) as error:
        transport.send(INIT)
    assert error.value.code == "MCP_SESSION_EXPIRED" and "10 second limit" in error.value.message


def test_the_request_limit_given_to_the_factory_reaches_the_transport() -> None:
    clock = Clock()

    def slow(request: httpx.Request) -> httpx.Response:
        def chunks() -> Iterator[bytes]:
            clock.now += 3.0
            yield b": slow\n"

        return httpx.Response(200, content=chunks(), headers={"content-type": "text/event-stream"})

    opener = HttpMcpTransportFactory(
        lambda: httpx.Client(transport=httpx.MockTransport(slow)),
        Pinner(),
        {},
        request_seconds=2.0,
        clock=clock,
    )
    with pytest.raises(TransientStageError, match="in 2 seconds"):
        opener.open(URL, "").send(INIT)
