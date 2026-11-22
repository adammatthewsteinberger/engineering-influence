# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""McpCommand, the inspection, a finding, an addition, and adding a server to a lock."""

from typing import Any

import pytest

from engineering_influence.models.mcp_command import McpCommand
from engineering_influence.models.mcp_server_info import McpServerInfo
from engineering_influence.models.mcp_server_inspection import McpServerInspection
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.mcp_tool_set import McpToolSet
from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.models.tool_lock_addition import ToolLockAddition
from engineering_influence.models.tool_lock_finding import ToolLockFinding

A = "a" * 64


def server(name: str = "files", tools_hash: str = A) -> McpServerLock:
    return McpServerLock(
        name=name,
        command=("/usr/bin/server",),
        files=(("/usr/bin/server", A),),
        env=(),
        server_name="s",
        server_version="1",
        tool_names=(),
        tools_hash=tools_hash,
    )


# ------------------------------------------------------------------------------ the command
def test_a_command_is_an_absolute_executable_and_its_arguments() -> None:
    assert McpCommand(("/usr/bin/node", "/opt/x.js", "--flag")).argv[0] == "/usr/bin/node"


@pytest.mark.parametrize("argv", [(), ["/usr/bin/x"]])
def test_a_command_is_a_non_empty_tuple(argv: Any) -> None:
    with pytest.raises(ValueError, match="non-empty tuple"):
        McpCommand(argv)


@pytest.mark.parametrize("part", ["", 5, None])
def test_every_part_is_a_non_empty_string(part: Any) -> None:
    with pytest.raises(ValueError, match="non-empty string"):
        McpCommand(("/usr/bin/x", part))


def test_the_executable_is_an_absolute_path() -> None:
    with pytest.raises(ValueError, match="absolute path of its executable"):
        McpCommand(("node",))


@pytest.mark.parametrize("launcher", sorted(McpCommand.LAUNCHERS))
def test_a_launcher_is_refused_wherever_it_lives(launcher: str) -> None:
    with pytest.raises(ValueError, match=f"{launcher} fetches code that cannot be hashed"):
        McpCommand((f"/opt/somewhere/{launcher}", "pkg"))


def test_a_name_that_only_contains_a_launchers_name_is_fine() -> None:
    assert McpCommand(("/opt/npx-tools/server",)).argv == ("/opt/npx-tools/server",)


# -------------------------------------------------------------------------- inspection etc.
def test_an_inspection_holds_what_the_server_said() -> None:
    info, tools = McpServerInfo("s", "1", "p"), McpToolSet(())
    inspection = McpServerInspection(info, tools)
    assert (inspection.info, inspection.tools) == (info, tools)


def test_an_addition_holds_the_new_lock_the_entry_and_what_the_server_said() -> None:
    entry = server()
    inspection = McpServerInspection(McpServerInfo("s", "1", "p"), McpToolSet(()))
    addition = ToolLockAddition(ToolLock((entry,)), entry, inspection)
    assert addition.server is entry and addition.lock.servers == (entry,)


def test_a_finding_with_no_problems_passes_with_one_ok_line() -> None:
    finding = ToolLockFinding("files", ())
    assert finding.passed() and finding.lines() == ("ok    files",)


def test_a_finding_with_problems_fails_with_a_line_for_each() -> None:
    finding = ToolLockFinding("files", ("first thing", "second thing"))
    assert not finding.passed()
    assert finding.lines() == ("FAIL  files: first thing", "FAIL  files: second thing")


def test_anything_not_printable_a_server_said_is_shown_as_a_space() -> None:
    finding = ToolLockFinding("files", ("it said \x1b[31mred\x1b[0m\r\nand \x07 more",))
    [line] = finding.lines()
    assert "\x1b" not in line and "\r" not in line and "\n" not in line and "\x07" not in line
    assert "red" in line and "and" in line


# --------------------------------------------------------------------------- with_server
def test_a_server_is_added_after_the_ones_there() -> None:
    added = ToolLock((server("a"),)).with_server(server("b"), replace=False)
    assert [s.name for s in added.servers] == ["a", "b"]


def test_a_server_that_is_already_there_is_refused_unless_replacing() -> None:
    with pytest.raises(ValueError, match="a server named 'a' is already locked"):
        ToolLock((server("a"),)).with_server(server("a"), replace=False)


def test_replacing_swaps_the_entry_and_keeps_the_others() -> None:
    old, new = server("a"), server("a", tools_hash="b" * 64)
    result = ToolLock((old, server("z"))).with_server(new, replace=True)
    assert result.server("a") is new and result.server("z") is not None and len(result.servers) == 2


def test_replacing_a_server_that_is_not_there_just_adds_it() -> None:
    assert ToolLock().with_server(server("a"), replace=True).names() == ("a",)
