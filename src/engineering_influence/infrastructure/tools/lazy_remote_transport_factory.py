# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Builds the remote transport factory only when a remote server is first contacted."""

from collections.abc import Callable

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.mcp_remote_transport_factory_interface import (
    McpRemoteTransportFactoryInterface,
)
from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface


class LazyRemoteTransportFactory(McpRemoteTransportFactoryInterface):
    """So an install without the ``runtime`` extra still runs every command that has no remote server.

    The HTTP transport needs ``httpx``, which the core install does not have. Building it is deferred to
    the first remote server, and a missing dependency becomes an error that names the extra to install
    instead of a traceback. Once built, the factory is kept.
    """

    def __init__(self, build: Callable[[], McpRemoteTransportFactoryInterface]) -> None:
        """Remember the function that builds the real remote transport factory, to call it on first use."""
        self._build = build
        self._factory: McpRemoteTransportFactoryInterface | None = None

    def open(self, url: str, bearer_env: str) -> McpTransportInterface:
        """Build the real factory if this is the first remote server, then let it open the transport."""
        if self._factory is None:
            try:
                self._factory = self._build()
            except ImportError as error:
                raise ApplicationError(
                    code="TOOL_REMOTE_NEEDS_EXTRA",
                    message="a remote tool server needs the runtime extra: "
                    "pip install 'engineering-influence[runtime]' "
                    f"(missing {error.name or 'a dependency'})",
                    http_status=503,
                ) from error
        return self._factory.open(url, bearer_env)
