# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ToolLockEditor: everything that can be refused is refused before the command is run."""

from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.executable_finder_interface import ExecutableFinderInterface
from engineering_influence.interfaces.file_hasher_interface import FileHasherInterface
from engineering_influence.models.mcp_server_info import McpServerInfo
from engineering_influence.models.mcp_server_inspection import McpServerInspection
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.mcp_tool_descriptor import McpToolDescriptor
from engineering_influence.models.mcp_tool_set import McpToolSet
from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.services.interfaces.mcp_server_probe_interface import (
    McpServerProbeInterface,
)
from engineering_influence.services.interfaces.tool_lock_editor_interface import (
    ToolLockEditorInterface,
)
from engineering_influence.services.tool_lock_editor import ToolLockEditor

NODE, SCRIPT = "/usr/bin/node", "/opt/mcp/index.js"
TOOLS = McpToolSet(
    (
        McpToolDescriptor("read", "Reads.", {"type": "object"}),
        McpToolDescriptor("write", "Writes.", {"type": "object"}),
    )
)
INSPECTION = McpServerInspection(McpServerInfo("files-server", "1.2.0", "2025-06-18"), TOOLS)


class Probe(McpServerProbeInterface):
    def __init__(self, fail: BaseException | None = None) -> None:
        self.fail = fail
        self.inspected: list[tuple[tuple[str, ...], tuple[str, ...]]] = []
        self.contacted: list[tuple[str, str]] = []

    def inspect(self, command: tuple[str, ...], env_names: tuple[str, ...]) -> McpServerInspection:
        self.inspected.append((command, env_names))
        if self.fail:
            raise self.fail
        return INSPECTION

    def inspect_remote(self, url: str, bearer_env: str) -> McpServerInspection:
        self.contacted.append((url, bearer_env))
        if self.fail:
            raise self.fail
        return INSPECTION

    def check(self, entry: McpServerLock) -> tuple[str, ...]:
        return ()


class Hasher(FileHasherInterface):
    def __init__(self, files: dict[str, str | None] | None = None) -> None:
        self.files = {NODE: "a" * 64, SCRIPT: "b" * 64} if files is None else files

    def digest(self, path: str) -> str | None:
        return self.files.get(path)


class Finder(ExecutableFinderInterface):
    def __init__(self, found: dict[str, str] | None = None) -> None:
        self.found = {"node": NODE} if found is None else found

    def find(self, name: str) -> str | None:
        return self.found.get(name)


def editor(probe: Probe | None = None, hasher: Hasher | None = None, finder: Finder | None = None):
    made = probe or Probe()
    return ToolLockEditor(made, hasher or Hasher(), finder or Finder()), made


def add(
    argv: tuple[str, ...] = ("node", SCRIPT),
    *,
    lock: ToolLock | None = None,
    name: str = "files",
    env: tuple[str, ...] = (),
    replace: bool = False,
    probe: Probe | None = None,
    hasher: Hasher | None = None,
    finder: Finder | None = None,
):
    tool_editor, made = editor(probe, hasher, finder)
    return tool_editor.add(lock or ToolLock(), name, argv, env, replace), made


def refused(
    code: str, argv: tuple[str, ...] = ("node", SCRIPT), **kwargs: Any
) -> tuple[ApplicationError, Probe]:
    probe = kwargs.pop("probe", None) or Probe()
    with pytest.raises(ApplicationError) as error:
        add(argv, probe=probe, **kwargs)
    status = 502 if code == "TOOL_SERVER_UNRESPONSIVE" else 422
    assert (error.value.code, error.value.http_status) == (code, status)
    return error.value, probe


def test_it_is_a_lock_editor() -> None:
    assert isinstance(editor()[0], ToolLockEditorInterface)


def test_a_server_is_run_once_and_recorded_with_what_it_said() -> None:
    result, probe = add(env=("FILES_ROOT",))
    server = result.server
    assert probe.inspected == [((NODE, SCRIPT), ("FILES_ROOT",))]
    assert server.command == (NODE, SCRIPT) and server.env == ("FILES_ROOT",)
    assert (server.server_name, server.server_version) == ("files-server", "1.2.0")
    assert server.tool_names == ("read", "write") and server.tools_hash == TOOLS.digest()
    assert result.lock.servers == (server,) and result.inspection is INSPECTION


def test_the_executable_and_each_script_are_hashed_sorted_by_path() -> None:
    server = add()[0].server
    assert server.files == ((SCRIPT, "b" * 64), (NODE, "a" * 64))
    assert server.file_hashes() == {SCRIPT: "b" * 64, NODE: "a" * 64}


def test_arguments_that_are_not_files_are_not_hashed() -> None:
    server = add(("node", SCRIPT, "--port", "8080"))[0].server
    assert [path for path, _ in server.files] == [SCRIPT, NODE]


def test_the_command_name_is_made_absolute_by_the_finder() -> None:
    assert add(("node", SCRIPT))[0].server.command[0] == NODE


def test_the_new_lock_keeps_what_was_there() -> None:
    other, _ = add(name="other")
    result, _ = add(lock=other.lock)
    assert result.lock.names() == ("files", "other")


@pytest.mark.parametrize("name", ["", "Files", "1x", "a_b", "a" * 33])
def test_a_name_that_is_not_allowed_is_refused_before_anything_runs(name: str) -> None:
    _, probe = refused("TOOL_NAME_INVALID", name=name)
    assert probe.inspected == []


def test_a_name_already_locked_is_refused_unless_replacing() -> None:
    existing, _ = add()
    error, probe = refused("TOOL_LOCK_EXISTS", lock=existing.lock)
    assert "already locked" in error.message and "--replace" in error.message
    assert probe.inspected == []
    replaced, _ = add(lock=existing.lock, replace=True)
    assert len(replaced.lock.servers) == 1


@pytest.mark.parametrize("env", [("lower",), ("A", "A"), ("1A",)])
def test_bad_environment_names_are_refused_before_anything_runs(env: tuple[str, ...]) -> None:
    _, probe = refused("TOOL_ENV_INVALID", env=env)
    assert probe.inspected == []


def test_a_command_that_does_not_exist_is_refused_before_anything_runs() -> None:
    error, probe = refused("TOOL_COMMAND_NOT_FOUND", ("nonexistent", SCRIPT))
    assert "'nonexistent'" in error.message and probe.inspected == []


def test_a_launcher_is_refused_before_anything_runs() -> None:
    error, probe = refused(
        "TOOL_COMMAND_REFUSED", ("npx", "some-server"), finder=Finder({"npx": "/usr/bin/npx"})
    )
    assert "npx fetches code that cannot be hashed" in error.message and probe.inspected == []


def test_an_executable_that_cannot_be_read_is_refused() -> None:
    error, probe = refused("TOOL_FILE_UNREADABLE", hasher=Hasher({SCRIPT: "b" * 64}))
    assert NODE in error.message and probe.inspected == []


def test_a_script_given_by_a_relative_path_is_refused_so_the_file_locked_is_the_file_run() -> None:
    error, probe = refused(
        "TOOL_RELATIVE_SCRIPT",
        ("node", "index.js"),
        hasher=Hasher({NODE: "a" * 64, "index.js": "c" * 64}),
    )
    assert (
        "'index.js'" in error.message and "absolute path" in error.message and probe.inspected == []
    )


def test_a_server_that_does_not_answer_in_time_is_a_502() -> None:
    error, _ = refused(
        "TOOL_SERVER_UNRESPONSIVE",
        probe=Probe(TransientStageError("did not answer within 30 seconds")),
    )
    assert error.message == "did not answer within 30 seconds"


def test_a_server_that_fails_is_the_probes_error_untouched() -> None:
    failure = ApplicationError(code="MCP_SERVER_CLOSED", message="it died", http_status=502)
    tool_editor, _ = editor(Probe(failure))
    with pytest.raises(ApplicationError) as error:
        tool_editor.add(ToolLock(), "files", ("node", SCRIPT), (), False)
    assert error.value is failure


def test_an_entry_the_model_refuses_is_reported_as_an_invalid_lock() -> None:
    error, _ = refused("TOOL_LOCK_INVALID", hasher=Hasher({NODE: "NOT-HEX", SCRIPT: "b" * 64}))
    assert "SHA-256" in error.message


# ------------------------------------------------------------------------------ a remote server
URL = "https://mcp.example.com/mcp"


def add_remote(
    url: str = URL,
    *,
    lock: ToolLock | None = None,
    name: str = "docs",
    bearer_env: str = "DOCS_TOKEN",
    replace: bool = False,
    probe: Probe | None = None,
):
    tool_editor, made = editor(probe)
    return tool_editor.add_remote(lock or ToolLock(), name, url, bearer_env, replace), made


def refused_remote(code: str, **kwargs: Any) -> tuple[ApplicationError, Probe]:
    probe = kwargs.pop("probe", None) or Probe()
    with pytest.raises(ApplicationError) as error:
        add_remote(probe=probe, **kwargs)
    assert (error.value.code, error.value.http_status) == (
        code,
        502 if "UNRESPONSIVE" in code else 422,
    )
    return error.value, probe


def test_a_remote_server_is_contacted_once_and_recorded_by_its_address_and_what_it_said() -> None:
    result, probe = add_remote()
    server = result.server
    assert probe.contacted == [(URL, "DOCS_TOKEN")] and probe.inspected == []
    assert server.remote() and server.url == URL and server.bearer_env == "DOCS_TOKEN"
    assert server.command == () and server.files == () and server.env == ()
    assert (server.server_name, server.server_version) == ("files-server", "1.2.0")
    assert server.tool_names == ("read", "write") and server.tools_hash == TOOLS.digest()
    assert result.lock.servers == (server,) and result.inspection is INSPECTION


def test_a_remote_server_needs_no_bearer_variable() -> None:
    result, probe = add_remote(bearer_env="")
    assert probe.contacted == [(URL, "")] and result.server.bearer_env == ""


def test_a_remote_server_can_be_added_to_a_lock_with_local_ones_and_replaced() -> None:
    local, _ = add()
    result, _ = add_remote(lock=local.lock)
    assert result.lock.names() == ("docs", "files")
    error, probe = refused_remote("TOOL_LOCK_EXISTS", lock=result.lock)
    assert "--replace" in error.message and probe.contacted == []
    assert len(add_remote(lock=result.lock, replace=True)[0].lock.servers) == 2


@pytest.mark.parametrize("name", ["", "Docs", "1x", "a_b", "a" * 33])
def test_a_bad_remote_name_is_refused_before_anything_is_contacted(name: str) -> None:
    _, probe = refused_remote("TOOL_NAME_INVALID", name=name)
    assert probe.contacted == []


@pytest.mark.parametrize(
    "url",
    [
        "http://mcp.example.com/mcp",
        "https://user:pw@mcp.example.com/mcp",
        "https://mcp.example.com/mcp?token=abc",
        "https://mcp.example.com/mcp#frag",
        "https:///mcp",
        "https://mcp.example.com/a b",
        "",
    ],
)
def test_an_address_that_is_not_plain_https_is_refused_before_anything_is_contacted(
    url: str,
) -> None:
    _, probe = refused_remote("TOOL_URL_REFUSED", url=url)
    assert probe.contacted == []


@pytest.mark.parametrize("bearer_env", ["lower", "1A", "A B"])
def test_a_bad_bearer_variable_is_refused_before_anything_is_contacted(bearer_env: str) -> None:
    _, probe = refused_remote("TOOL_ENV_INVALID", bearer_env=bearer_env)
    assert probe.contacted == []


def test_a_remote_server_that_does_not_answer_in_time_is_a_502() -> None:
    error, _ = refused_remote(
        "TOOL_SERVER_UNRESPONSIVE",
        probe=Probe(TransientStageError("mcp.example.com did not finish answering")),
    )
    assert error.message == "mcp.example.com did not finish answering"


def test_a_remote_server_that_fails_is_the_probes_error_untouched() -> None:
    failure = ApplicationError(code="MCP_AUTH_REFUSED", message="refused", http_status=502)
    tool_editor, _ = editor(Probe(failure))
    with pytest.raises(ApplicationError) as error:
        tool_editor.add_remote(ToolLock(), "docs", URL, "", False)
    assert error.value is failure
