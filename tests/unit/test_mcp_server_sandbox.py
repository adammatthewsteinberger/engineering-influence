# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The sandbox this system uses, and a refusal, not a plain start, where it has none."""

from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.tools.bubblewrap_command import BubblewrapCommand
from engineering_influence.infrastructure.tools.mcp_server_sandbox import McpServerSandbox
from engineering_influence.infrastructure.tools.sandbox_exec_profile import SandboxExecProfile

HOME = Path("/home/x")
FOUND = {"sandbox-exec": "/usr/bin/sandbox-exec", "bwrap": "/usr/bin/bwrap"}


def locate(name: str) -> str | None:
    return FOUND.get(name)


def test_macos_uses_sandbox_exec_when_it_is_there() -> None:
    sandbox = McpServerSandbox("darwin", locate, HOME)
    assert sandbox.wrap(("/bin/s",), Path("/tmp/w"))[0] == "/usr/bin/sandbox-exec"


def test_linux_uses_bubblewrap_when_it_is_there() -> None:
    sandbox = McpServerSandbox("linux", locate, HOME)
    assert sandbox.wrap(("/bin/s",), Path("/tmp/w"))[0] == "/usr/bin/bwrap"


def test_linux_with_a_different_suffix_still_counts_as_linux() -> None:
    assert McpServerSandbox("linux2", locate, HOME).wrap(("/bin/s",), Path("/tmp/w"))[0] == (
        "/usr/bin/bwrap"
    )


@pytest.mark.parametrize(
    ("platform", "found"),
    [("darwin", {}), ("linux", {}), ("win32", FOUND), ("freebsd", FOUND)],
)
def test_a_system_without_a_native_sandbox_refuses_to_start_a_server(
    platform: str, found: dict[str, str]
) -> None:
    sandbox = McpServerSandbox(platform, lambda name: found.get(name), HOME)
    with pytest.raises(ApplicationError) as raised:
        sandbox.wrap(("/bin/s",), Path("/tmp/w"))
    assert (raised.value.code, raised.value.http_status) == ("SANDBOX_UNAVAILABLE", 503)
    assert "is not started without one" in raised.value.message


def test_the_choice_is_the_confinement_class_itself() -> None:
    assert isinstance(McpServerSandbox._choose("darwin", locate, HOME), SandboxExecProfile)
    assert isinstance(McpServerSandbox._choose("linux", locate, HOME), BubblewrapCommand)
    assert McpServerSandbox._choose("win32", locate, HOME) is None
