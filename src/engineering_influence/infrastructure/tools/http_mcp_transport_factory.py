# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Prepares conversations with remote MCP servers, each with a client of its own."""

import time
from collections.abc import Callable, Mapping

import httpx

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.tools.http_mcp_transport import HttpMcpTransport
from engineering_influence.interfaces.mcp_remote_transport_factory_interface import (
    McpRemoteTransportFactoryInterface,
)
from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface
from engineering_influence.interfaces.outbound_url_pinner_interface import (
    OutboundUrlPinnerInterface,
)
from engineering_influence.models.mcp_endpoint_url import McpEndpointUrl


class HttpMcpTransportFactory(McpRemoteTransportFactoryInterface):
    """Checks the address and the credential, then hands back a transport that owns a new client.

    The address is checked by ``McpEndpointUrl`` again here, because a lock is a file a person can
    edit. The credential is read from the environment by the variable's name at this moment and is
    never kept anywhere else: a variable that is not set, or whose value is not a bearer token
    (printable characters, no spaces), refuses the server rather than sending it a blank or a broken
    header. The client is built by the injected function and is closed with the transport, so each
    session has its own connection pool and its own (empty) cookie jar.
    """

    def __init__(
        self,
        clients: Callable[[], httpx.Client],
        pinner: OutboundUrlPinnerInterface,
        environ: Mapping[str, str],
        request_seconds: float = 30.0,
        session_seconds: float = 4 * 3600.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        """Remember the client factory, the address pinner, the environment and the request and session time limits."""
        self._clients = clients
        self._pinner = pinner
        self._environ = environ
        self._request_seconds = request_seconds
        self._session_seconds = session_seconds
        self._clock = clock

    def open(self, url: str, bearer_env: str) -> McpTransportInterface:
        """Prepare to talk to the server at ``url``, with the token in ``bearer_env`` if one is named."""
        try:
            McpEndpointUrl(url)
        except (ValueError, TypeError) as error:
            raise ApplicationError(
                code="TOOL_URL_REFUSED", message=str(error), http_status=422
            ) from error
        token = self._token(bearer_env)
        return HttpMcpTransport(
            self._clients(),
            url,
            self._pinner,
            token,
            request_seconds=self._request_seconds,
            session_seconds=self._session_seconds,
            clock=self._clock,
        )

    def _token(self, name: str) -> str | None:
        if not name:
            return None
        value = self._environ.get(name, "")
        if not value:
            raise ApplicationError(
                code="TOOL_ENV_MISSING",
                message=f"the environment variable {name} is not set",
                http_status=422,
            )
        if any(not 0x21 <= ord(char) <= 0x7E for char in value):
            raise ApplicationError(
                code="TOOL_ENV_INVALID",
                message=f"{name} is not a bearer token: printable characters, no spaces",
                http_status=422,
            )
        return value
