# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ToolLockEditor.grant and .revoke: they change who may call what and run nothing."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.executable_finder_interface import ExecutableFinderInterface
from engineering_influence.interfaces.file_hasher_interface import FileHasherInterface
from engineering_influence.models.mcp_server_inspection import McpServerInspection
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.services.interfaces.mcp_server_probe_interface import (
    McpServerProbeInterface,
)
from engineering_influence.services.tool_lock_editor import ToolLockEditor

A = "a" * 64


class Probe(McpServerProbeInterface):
    def __init__(self) -> None:
        self.used = 0

    def inspect(self, command: tuple[str, ...], env_names: tuple[str, ...]) -> McpServerInspection:
        self.used += 1
        raise NotImplementedError

    def inspect_remote(self, url: str, bearer_env: str) -> McpServerInspection:
        self.used += 1
        raise NotImplementedError

    def check(self, entry: McpServerLock) -> tuple[str, ...]:
        self.used += 1
        return ()


class Hasher(FileHasherInterface):
    def digest(self, path: str) -> str | None:
        self.used = True
        return None


class Finder(ExecutableFinderInterface):
    def find(self, name: str) -> str | None:
        return None


def locked(grants: tuple[tuple[str, tuple[str, ...]], ...] = ()) -> ToolLock:
    return ToolLock(
        (
            McpServerLock(
                name="files",
                command=("/usr/bin/s",),
                files=(("/usr/bin/s", A),),
                env=(),
                server_name="s",
                server_version="1",
                tool_names=("list", "read", "write"),
                tools_hash=A,
                grants=grants,
            ),
        )
    )


def editor() -> tuple[ToolLockEditor, Probe]:
    probe = Probe()
    return ToolLockEditor(probe, Hasher(), Finder()), probe


def refused(call, code: str) -> ApplicationError:  # type: ignore[no-untyped-def]
    with pytest.raises(ApplicationError) as error:
        call()
    assert (error.value.code, error.value.http_status) == (code, 422)
    return error.value


def granted(lock: ToolLock, stage: str = "research") -> tuple[str, ...]:
    server = lock.server("files")
    assert server is not None
    return server.granted(stage)


def test_a_grant_adds_tools_to_a_stage_and_runs_nothing() -> None:
    tool_editor, probe = editor()
    first = tool_editor.grant(locked(), "files", "research", ("read",))
    second = tool_editor.grant(first, "files", "research", ("write",))
    assert granted(first) == ("read",) and granted(second) == ("read", "write")
    assert probe.used == 0


def test_a_grant_for_a_server_that_is_not_locked_is_refused() -> None:
    tool_editor, _ = editor()
    error = refused(
        lambda: tool_editor.grant(locked(), "nope", "research", ("read",)), "TOOL_SERVER_UNKNOWN"
    )
    assert error.message == "no server named 'nope' is locked"


def test_a_grant_that_names_no_tool_is_refused() -> None:
    tool_editor, _ = editor()
    error = refused(
        lambda: tool_editor.grant(locked(), "files", "research", ()), "TOOL_GRANT_INVALID"
    )
    assert "at least one tool" in error.message


@pytest.mark.parametrize(
    ("stage", "tools", "reason"),
    [
        ("research", ("delete",), "not one of the tools this lock lists"),
        ("Bad Stage", ("read",), "names a stage"),
    ],
)
def test_a_grant_the_model_refuses_is_reported_as_invalid(
    stage: str, tools: tuple[str, ...], reason: str
) -> None:
    tool_editor, _ = editor()
    error = refused(
        lambda: tool_editor.grant(locked(), "files", stage, tools), "TOOL_GRANT_INVALID"
    )
    assert reason in error.message


def test_revoking_named_tools_leaves_the_rest() -> None:
    tool_editor, probe = editor()
    result = tool_editor.revoke(
        locked((("research", ("list", "read", "write")),)), "files", "research", ("read",)
    )
    assert granted(result) == ("list", "write") and probe.used == 0


def test_revoking_with_no_tools_named_takes_them_all() -> None:
    tool_editor, _ = editor()
    result = tool_editor.revoke(
        locked((("outline", ("read",)), ("research", ("list", "read")))), "files", "research", ()
    )
    assert granted(result) == () and granted(result, "outline") == ("read",)


def test_revoking_from_a_stage_with_no_grant_is_refused_so_a_typo_is_noticed() -> None:
    tool_editor, _ = editor()
    error = refused(
        lambda: tool_editor.revoke(locked(), "files", "reserch", ()), "TOOL_GRANT_UNKNOWN"
    )
    assert error.message == "stage 'reserch' has no grant from 'files'"


def test_revoking_from_a_server_that_is_not_locked_is_refused() -> None:
    tool_editor, _ = editor()
    refused(lambda: tool_editor.revoke(locked(), "nope", "research", ()), "TOOL_SERVER_UNKNOWN")
