# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ToolLockVerifier: is a locked server still the one a person approved?"""

from engineering_influence.interfaces.file_hasher_interface import FileHasherInterface
from engineering_influence.models.mcp_server_info import McpServerInfo
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.mcp_tool_descriptor import McpToolDescriptor
from engineering_influence.models.mcp_tool_set import McpToolSet
from engineering_influence.services.interfaces.tool_lock_verifier_interface import (
    ToolLockVerifierInterface,
)
from engineering_influence.services.tool_lock_verifier import ToolLockVerifier

EXE, SCRIPT = "/usr/bin/server", "/opt/server.js"
OBJECT = {"type": "object"}


class Hasher(FileHasherInterface):
    def __init__(self, files: dict[str, str | None]) -> None:
        self.files = files

    def digest(self, path: str) -> str | None:
        return self.files.get(path)


def tools(*names: str, description: str = "d") -> McpToolSet:
    return McpToolSet(tuple(McpToolDescriptor(name, description, OBJECT) for name in names))


LOCKED_TOOLS = tools("read", "write")
LOCKED = McpServerLock(
    name="files",
    command=(EXE, SCRIPT, "--flag", "-v"),
    files=((SCRIPT, "b" * 64), (EXE, "a" * 64)),
    env=(),
    server_name="files-server",
    server_version="1.2.0",
    tool_names=LOCKED_TOOLS.names(),
    tools_hash=LOCKED_TOOLS.digest(),
)
INFO = McpServerInfo("files-server", "1.2.0", "2025-06-18")


def verifier() -> ToolLockVerifier:
    return ToolLockVerifier(Hasher({EXE: "a" * 64, SCRIPT: "b" * 64}))


def test_it_is_a_verifier() -> None:
    assert isinstance(verifier(), ToolLockVerifierInterface)


# ------------------------------------------------------------------------------------ files
def test_files_that_are_as_locked_have_no_problems() -> None:
    assert verifier().check_files(LOCKED) == ()


def test_a_file_that_changed_is_named() -> None:
    hasher = ToolLockVerifier(Hasher({EXE: "a" * 64, SCRIPT: "c" * 64}))
    assert hasher.check_files(LOCKED) == (f"{SCRIPT} has changed since it was locked",)


def test_a_file_that_is_gone_or_not_a_regular_file_is_named() -> None:
    hasher = ToolLockVerifier(Hasher({EXE: None, SCRIPT: "b" * 64}))
    assert hasher.check_files(LOCKED) == (f"{EXE} is missing or is not a regular file",)


def test_every_problem_is_reported_not_just_the_first() -> None:
    hasher = ToolLockVerifier(Hasher({EXE: "x" * 64, SCRIPT: None}))
    assert hasher.check_files(LOCKED) == (
        f"{SCRIPT} is missing or is not a regular file",
        f"{EXE} has changed since it was locked",
    )


def test_a_file_added_to_the_command_is_noticed_because_it_is_not_locked() -> None:
    extra = "/opt/extra.js"
    changed = McpServerLock(
        name="files",
        command=(EXE, SCRIPT, extra),
        files=LOCKED.files,
        env=(),
        server_name="files-server",
        server_version="1.2.0",
        tool_names=LOCKED.tool_names,
        tools_hash=LOCKED.tools_hash,
    )
    hasher = ToolLockVerifier(Hasher({EXE: "a" * 64, SCRIPT: "b" * 64, extra: "d" * 64}))
    assert hasher.check_files(changed) == (f"{extra} is named in the command but is not locked",)


def test_arguments_that_are_not_files_are_not_a_problem() -> None:
    hasher = ToolLockVerifier(Hasher({EXE: "a" * 64, SCRIPT: "b" * 64, "--flag": None, "-v": None}))
    assert hasher.check_files(LOCKED) == ()


def test_the_executable_is_always_among_the_files_named_in_the_command() -> None:
    only_exe = McpServerLock(
        name="files",
        command=(EXE,),
        files=((EXE, "a" * 64),),
        env=(),
        server_name="s",
        server_version="1",
        tool_names=(),
        tools_hash="a" * 64,
    )
    assert ToolLockVerifier(Hasher({EXE: "a" * 64})).check_files(only_exe) == ()


# ------------------------------------------------------------------------------- the server
def test_a_server_that_reports_what_was_locked_has_no_problems() -> None:
    assert verifier().check_server(LOCKED, INFO, LOCKED_TOOLS) == ()


def test_a_different_name_or_version_is_named() -> None:
    renamed = McpServerInfo("evil-server", "1.2.0", "p")
    bumped = McpServerInfo("files-server", "2.0.0", "p")
    assert verifier().check_server(LOCKED, renamed, LOCKED_TOOLS) == (
        "the server now calls itself 'evil-server', not 'files-server'",
    )
    assert verifier().check_server(LOCKED, bumped, LOCKED_TOOLS) == (
        "the server is now version '2.0.0', not '1.2.0'",
    )


def test_the_protocol_version_is_not_part_of_the_lock() -> None:
    other = McpServerInfo("files-server", "1.2.0", "2024-11-05")
    assert verifier().check_server(LOCKED, other, LOCKED_TOOLS) == ()


def test_tools_that_were_added_and_removed_are_named() -> None:
    now = tools("read", "delete", "exec")
    [problem] = verifier().check_server(LOCKED, INFO, now)
    assert problem == (
        "the tools the server advertises have changed (added 'delete', 'exec'; removed 'write')"
    )


def test_only_added_or_only_removed_says_only_that() -> None:
    [added] = verifier().check_server(LOCKED, INFO, tools("read", "write", "extra"))
    [removed] = verifier().check_server(LOCKED, INFO, tools("read"))
    assert added.endswith("(added 'extra')")
    assert removed.endswith("(removed 'write')")


def test_a_description_that_was_reworded_is_noticed_even_though_the_names_are_the_same() -> None:
    [problem] = verifier().check_server(
        LOCKED, INFO, tools("read", "write", description="d, now with instructions")
    )
    assert problem == (
        "the tools the server advertises have changed (a description or schema was reworded)"
    )


def test_a_long_list_of_names_is_cut_after_eight_and_says_how_many_more() -> None:
    many = tools("read", "write", *[f"t{n:02d}" for n in range(12)], "x" * 100)
    [problem] = verifier().check_server(LOCKED, INFO, many)
    assert "added 't00', 't01', 't02', 't03', 't04', 't05', 't06', 't07' and 5 more" in problem
    assert "t08" not in problem


def test_exactly_eight_added_names_are_all_shown_with_no_more_note() -> None:
    eight = tools("read", "write", *[f"t{n}" for n in range(8)])
    [problem] = verifier().check_server(LOCKED, INFO, eight)
    assert "'t7')" in problem and "more" not in problem


def test_a_hostile_servers_long_tool_name_is_shortened_to_sixty_characters() -> None:
    [problem] = verifier().check_server(LOCKED, INFO, tools("read", "write", "x" * 100))
    assert repr("x" * 60) in problem and "x" * 61 not in problem


def test_everything_that_differs_is_reported_together() -> None:
    other = McpServerInfo("evil", "9", "p")
    problems = verifier().check_server(LOCKED, other, tools("read"))
    assert len(problems) == 3


def test_check_is_the_files_then_the_server() -> None:
    hasher = ToolLockVerifier(Hasher({EXE: "z" * 64, SCRIPT: "b" * 64}))
    problems = hasher.check(LOCKED, McpServerInfo("evil", "1.2.0", "p"), LOCKED_TOOLS)
    assert problems == (
        f"{EXE} has changed since it was locked",
        "the server now calls itself 'evil', not 'files-server'",
    )
    assert verifier().check(LOCKED, INFO, LOCKED_TOOLS) == ()


# ------------------------------------------------------------------------------ a remote server
REMOTE = McpServerLock(
    name="docs",
    command=(),
    files=(),
    env=(),
    server_name="files-server",
    server_version="1.2.0",
    tool_names=LOCKED_TOOLS.names(),
    tools_hash=LOCKED_TOOLS.digest(),
    url="https://mcp.example.com/mcp",
)


def test_a_remote_server_has_no_files_to_check_and_the_hasher_is_never_asked() -> None:
    class Untouchable(FileHasherInterface):
        def digest(self, path: str) -> str | None:
            raise AssertionError("a remote server has nothing to hash")

    assert ToolLockVerifier(Untouchable()).check_files(REMOTE) == ()


def test_a_remote_server_is_still_held_to_its_name_version_and_tools() -> None:
    verifier = ToolLockVerifier(Hasher({}))
    info = McpServerInfo("files-server", "1.2.0", "2025-06-18")
    assert verifier.check(REMOTE, info, LOCKED_TOOLS) == ()
    problems = verifier.check(REMOTE, McpServerInfo("other", "9", "p"), tools("read"))
    assert len(problems) == 3 and "now calls itself 'other'" in problems[0]
