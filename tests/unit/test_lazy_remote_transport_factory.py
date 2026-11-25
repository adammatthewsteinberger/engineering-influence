# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""LazyRemoteTransportFactory: a minimal install runs everything that has no remote server."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.tools.lazy_remote_transport_factory import (
    LazyRemoteTransportFactory,
)
from engineering_influence.interfaces.mcp_remote_transport_factory_interface import (
    McpRemoteTransportFactoryInterface,
)
from engineering_influence.interfaces.mcp_transport_interface import McpTransportInterface

URL = "https://mcp.example.com/mcp"


class Transport(McpTransportInterface):
    def send(self, message):  # type: ignore[no-untyped-def]
        ...

    def receive(self, timeout_seconds):  # type: ignore[no-untyped-def]
        return {}

    def close(self) -> None: ...


class Real(McpRemoteTransportFactoryInterface):
    def __init__(self) -> None:
        self.opened: list[tuple[str, str]] = []
        self.transport = Transport()

    def open(self, url: str, bearer_env: str) -> McpTransportInterface:
        self.opened.append((url, bearer_env))
        return self.transport


def test_it_is_a_remote_transport_factory() -> None:
    assert isinstance(LazyRemoteTransportFactory(Real), McpRemoteTransportFactoryInterface)


def test_nothing_is_built_until_a_remote_server_is_contacted() -> None:
    built: list[Real] = []

    def build() -> Real:
        built.append(Real())
        return built[0]

    lazy = LazyRemoteTransportFactory(build)
    assert built == []
    assert lazy.open(URL, "TOKEN") is built[0].transport
    assert built[0].opened == [(URL, "TOKEN")]


def test_the_real_factory_is_built_once_and_kept() -> None:
    built: list[Real] = []

    def build() -> Real:
        built.append(Real())
        return built[-1]

    lazy = LazyRemoteTransportFactory(build)
    lazy.open(URL, "")
    lazy.open(URL, "OTHER")
    assert len(built) == 1 and built[0].opened == [(URL, ""), (URL, "OTHER")]


def test_a_missing_dependency_names_the_extra_to_install_instead_of_a_traceback() -> None:
    def build() -> Real:
        raise ModuleNotFoundError("No module named 'httpx'", name="httpx")

    with pytest.raises(ApplicationError) as error:
        LazyRemoteTransportFactory(build).open(URL, "")
    assert (error.value.code, error.value.http_status) == ("TOOL_REMOTE_NEEDS_EXTRA", 503)
    assert error.value.message == (
        "a remote tool server needs the runtime extra: "
        "pip install 'engineering-influence[runtime]' (missing httpx)"
    )


def test_an_import_error_with_no_name_still_gets_the_message() -> None:
    def build() -> Real:
        raise ImportError("broken")

    with pytest.raises(ApplicationError, match=r"\(missing a dependency\)"):
        LazyRemoteTransportFactory(build).open(URL, "")


def test_a_failed_build_is_tried_again_on_the_next_remote_server() -> None:
    attempts: list[int] = []

    def build() -> Real:
        attempts.append(1)
        if len(attempts) == 1:
            raise ImportError("not yet")
        return Real()

    lazy = LazyRemoteTransportFactory(build)
    with pytest.raises(ApplicationError):
        lazy.open(URL, "")
    assert isinstance(lazy.open(URL, ""), Transport)
