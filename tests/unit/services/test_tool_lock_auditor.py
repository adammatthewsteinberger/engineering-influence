# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ToolLockAuditor: every locked server checked in turn, and a misspelt name cannot look like a pass."""

import pytest

from engineering_influence.models.mcp_server_inspection import McpServerInspection
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.services.interfaces.mcp_server_probe_interface import (
    McpServerProbeInterface,
)
from engineering_influence.services.interfaces.tool_lock_auditor_interface import (
    ToolLockAuditorInterface,
)
from engineering_influence.services.tool_lock_auditor import ToolLockAuditor

A = "a" * 64


def entry(name: str) -> McpServerLock:
    return McpServerLock(
        name=name,
        command=("/usr/bin/s",),
        files=(("/usr/bin/s", A),),
        env=(),
        server_name="s",
        server_version="1",
        tool_names=(),
        tools_hash=A,
    )


class Probe(McpServerProbeInterface):
    def __init__(self, problems: dict[str, tuple[str, ...]] | None = None) -> None:
        self.problems = problems or {}
        self.checked: list[str] = []

    def inspect(self, command: tuple[str, ...], env_names: tuple[str, ...]) -> McpServerInspection:
        raise NotImplementedError

    def inspect_remote(self, url: str, bearer_env: str) -> McpServerInspection:
        raise NotImplementedError

    def check(self, entry: McpServerLock) -> tuple[str, ...]:
        self.checked.append(entry.name)
        return self.problems.get(entry.name, ())


LOCK = ToolLock((entry("zed"), entry("alpha"), entry("mid")))


def test_it_is_an_auditor() -> None:
    assert isinstance(ToolLockAuditor(Probe()), ToolLockAuditorInterface)


def test_with_no_names_every_server_is_checked_in_name_order() -> None:
    probe = Probe({"mid": ("it changed",)})
    findings = ToolLockAuditor(probe).audit(LOCK, ())
    assert probe.checked == ["alpha", "mid", "zed"]
    assert [(f.name, f.passed()) for f in findings] == [
        ("alpha", True),
        ("mid", False),
        ("zed", True),
    ]
    assert findings[1].problems == ("it changed",)


def test_named_servers_alone_are_checked() -> None:
    probe = Probe()
    findings = ToolLockAuditor(probe).audit(LOCK, ["zed", "alpha"])
    assert probe.checked == ["alpha", "zed"] and [f.name for f in findings] == ["alpha", "zed"]


def test_a_name_that_is_not_locked_is_an_error_and_nothing_is_started() -> None:
    probe = Probe()
    with pytest.raises(ValueError, match="no server named 'nope' is locked"):
        ToolLockAuditor(probe).audit(LOCK, ["alpha", "nope"])
    assert probe.checked == []


def test_an_empty_lock_has_nothing_to_check() -> None:
    assert ToolLockAuditor(Probe()).audit(ToolLock(), ()) == ()
