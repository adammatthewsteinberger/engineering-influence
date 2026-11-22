# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""McpEndpointUrl and a remote McpServerLock: an address and what the server advertises, and nothing that could hold a secret."""

from typing import Any

import pytest

from engineering_influence.models.interfaces.mcp_endpoint_url_interface import (
    McpEndpointUrlInterface,
)
from engineering_influence.models.mcp_endpoint_url import McpEndpointUrl
from engineering_influence.models.mcp_server_lock import McpServerLock

A = "a" * 64
URL = "https://mcp.example.com/v1/mcp"


def remote(**changes: Any) -> McpServerLock:
    fields: dict[str, Any] = {
        "name": "docs",
        "command": (),
        "files": (),
        "env": (),
        "server_name": "docs-server",
        "server_version": "2.0.0",
        "tool_names": ("read", "search"),
        "tools_hash": A,
        "url": URL,
        "bearer_env": "DOCS_TOKEN",
    }
    return McpServerLock(**{**fields, **changes})


# ------------------------------------------------------------------------------ the address
def test_an_https_address_with_a_host_and_a_path_is_accepted() -> None:
    endpoint = McpEndpointUrl("https://MCP.example.com:8443/a/b")
    assert isinstance(endpoint, McpEndpointUrlInterface)
    assert (
        endpoint.url == "https://MCP.example.com:8443/a/b" and endpoint.host() == "mcp.example.com"
    )


def test_the_longest_address_is_accepted_and_one_more_is_not() -> None:
    longest = "https://h.example/" + "a" * (McpEndpointUrl.MAX_LENGTH - len("https://h.example/"))
    assert McpEndpointUrl(longest).url == longest
    with pytest.raises(ValueError, match="1 to 2048 characters"):
        McpEndpointUrl(longest + "a")


@pytest.mark.parametrize(
    ("url", "why"),
    [
        ("", "1 to 2048 characters"),
        ("http://mcp.example.com/mcp", "never plain http"),
        ("ftp://mcp.example.com/mcp", "never plain http"),
        ("mcp.example.com/mcp", "never plain http"),
        ("https:///mcp", "names a host"),
        ("https://user@mcp.example.com/mcp", "no user or password"),
        ("https://user:pw@mcp.example.com/mcp", "no user or password"),
        ("https://mcp.example.com/mcp?key=abc", "no query string or fragment"),
        ("https://mcp.example.com/mcp?", "no query string or fragment"),
        ("https://mcp.example.com/mcp#top", "no query string or fragment"),
        ("https://mcp.example.com/a b", "printable ASCII"),
        ("https://mcp.example.com/é", "printable ASCII"),
        ("https://mcp.example.com/\n", "printable ASCII"),
        ("https://mcp.example.com:99999/mcp", "Port"),
        ("https://mcp.example.com:abc/mcp", "Port"),
    ],
)
def test_an_address_that_could_carry_a_secret_or_is_not_https_is_refused(
    url: str, why: str
) -> None:
    with pytest.raises(ValueError, match=why):
        McpEndpointUrl(url)


def test_an_address_that_is_not_text_is_refused() -> None:
    with pytest.raises(TypeError, match="text"):
        McpEndpointUrl(None)  # type: ignore[arg-type]


# ------------------------------------------------------------------------------ the lock entry
def test_a_remote_entry_is_an_address_and_what_the_server_advertised() -> None:
    server = remote()
    assert server.remote() is True
    assert server.url == URL and server.bearer_env == "DOCS_TOKEN"
    assert server.command == () and server.files == () and server.file_hashes() == {}


def test_a_remote_entry_does_not_need_a_bearer_variable() -> None:
    assert remote(bearer_env="").bearer_env == ""


def test_a_local_entry_is_not_remote() -> None:
    local = McpServerLock(
        name="files",
        command=("/usr/bin/server",),
        files=(("/usr/bin/server", A),),
        env=(),
        server_name="s",
        server_version="1",
        tool_names=("read",),
        tools_hash=A,
    )
    assert local.remote() is False and local.url == "" and local.bearer_env == ""


def test_a_remote_entry_can_be_granted_to_a_stage_like_any_other() -> None:
    granted = remote().with_grants("research", ("search",))
    assert granted.model_names("research") == ("docs__search",)
    assert granted.url == URL and granted.bearer_env == "DOCS_TOKEN"
    assert granted.without_grants("research", ()).grants == ()


@pytest.mark.parametrize(
    "changes",
    [
        {"command": ("/usr/bin/server",)},
        {"files": (("/usr/bin/server", A),)},
        {"env": ("TOKEN",)},
    ],
)
def test_a_remote_entry_cannot_also_be_a_command(changes: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="locks an address, not a command, files or variables"):
        remote(**changes)


@pytest.mark.parametrize("url", ["http://mcp.example.com/mcp", "https://h.example/x?k=v"])
def test_a_remote_entry_with_an_address_that_is_not_allowed_is_refused(url: str) -> None:
    with pytest.raises(ValueError):
        remote(url=url)


@pytest.mark.parametrize("name", ["token", "1TOKEN", "A B", "A" * 65])
def test_a_bearer_variable_must_look_like_an_environment_variable(name: str) -> None:
    with pytest.raises(ValueError, match="capital letters, digits and _"):
        remote(bearer_env=name)


def test_a_local_entry_cannot_have_a_bearer_variable() -> None:
    with pytest.raises(ValueError, match="only a remote server has a bearer variable"):
        McpServerLock(
            name="files",
            command=("/usr/bin/server",),
            files=(("/usr/bin/server", A),),
            env=(),
            server_name="s",
            server_version="1",
            tool_names=(),
            tools_hash=A,
            bearer_env="TOKEN",
        )


def test_an_entry_with_neither_an_address_nor_a_command_is_refused() -> None:
    with pytest.raises(ValueError, match="non-empty tuple"):
        remote(url="", bearer_env="")


@pytest.mark.parametrize("changes", [{"url": 5}, {"bearer_env": None}])
def test_an_address_or_a_variable_that_is_not_text_is_refused(changes: dict[str, Any]) -> None:
    with pytest.raises(TypeError, match="text"):
        remote(**changes)


def test_an_address_may_use_the_first_and_last_printable_characters() -> None:
    assert McpEndpointUrl("https://h.example/!~").url == "https://h.example/!~"
    with pytest.raises(ValueError, match="printable ASCII"):
        McpEndpointUrl("https://h.example/\x7f")


def test_an_address_that_is_none_is_not_text() -> None:
    with pytest.raises(TypeError, match="text"):
        remote(url=None)
