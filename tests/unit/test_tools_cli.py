# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ToolsCli over fakes: parsing, exit codes, and what is printed about a server's untrusted words."""

import argparse
from collections.abc import Collection, Mapping
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.cli.interfaces.tools_cli_interface import ToolsCliInterface
from engineering_influence.interactions.cli.tools_cli import ToolsCli
from engineering_influence.interfaces.tool_lock_store_interface import ToolLockStoreInterface
from engineering_influence.models.mcp_server_info import McpServerInfo
from engineering_influence.models.mcp_server_inspection import McpServerInspection
from engineering_influence.models.mcp_server_lock import McpServerLock
from engineering_influence.models.mcp_tool_descriptor import McpToolDescriptor
from engineering_influence.models.mcp_tool_set import McpToolSet
from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.models.tool_lock_addition import ToolLockAddition
from engineering_influence.models.tool_lock_finding import ToolLockFinding
from engineering_influence.services.interfaces.tool_lock_auditor_interface import (
    ToolLockAuditorInterface,
)
from engineering_influence.services.interfaces.tool_lock_editor_interface import (
    ToolLockEditorInterface,
)

A = "a" * 64


def server(
    name: str = "files", env: tuple[str, ...] = (), server_name: str = "files-server"
) -> McpServerLock:
    return McpServerLock(
        name=name,
        command=("/usr/bin/node", "/opt/x.js"),
        files=(("/opt/x.js", A), ("/usr/bin/node", A)),
        env=env,
        server_name=server_name,
        server_version="1.2.0",
        tool_names=("read",),
        tools_hash=A,
    )


def remote_server(
    name: str = "docs", url: str = "https://mcp.example.com/mcp", bearer_env: str = ""
) -> McpServerLock:
    return McpServerLock(
        name=name,
        command=(),
        files=(),
        env=(),
        server_name="docs-server",
        server_version="2.0.0",
        tool_names=("read",),
        tools_hash=A,
        url=url,
        bearer_env=bearer_env,
    )


class Store(ToolLockStoreInterface):
    def __init__(self, lock: ToolLock | None = None, fail: BaseException | None = None) -> None:
        self.lock, self.fail = lock, fail
        self.loaded: list[Path] = []
        self.saved: list[tuple[Path, ToolLock]] = []

    def load(self, path: Path) -> ToolLock | None:
        self.loaded.append(path)
        if self.fail:
            raise self.fail
        return self.lock

    def save(self, path: Path, lock: ToolLock) -> None:
        self.saved.append((path, lock))


class Editor(ToolLockEditorInterface):
    def __init__(
        self, tools: tuple[McpToolDescriptor, ...] = (), fail: BaseException | None = None
    ) -> None:
        self.tools = tools or (McpToolDescriptor("read", "Reads a file.", {"type": "object"}),)
        self.fail = fail
        self.calls: list[tuple[ToolLock, str, tuple[str, ...], tuple[str, ...], bool]] = []
        self.remote_calls: list[tuple[ToolLock, str, str, str, bool]] = []
        self.edits: list[tuple[str, str, str, tuple[str, ...]]] = []

    def add(
        self,
        lock: ToolLock,
        name: str,
        argv: tuple[str, ...],
        env_names: tuple[str, ...],
        replace: bool,
    ) -> ToolLockAddition:
        self.calls.append((lock, name, argv, env_names, replace))
        if self.fail:
            raise self.fail
        entry = server(name)
        inspection = McpServerInspection(
            McpServerInfo("files-server", "1.2.0", "p"), McpToolSet(self.tools)
        )
        return ToolLockAddition(lock.with_server(entry, replace), entry, inspection)

    def add_remote(
        self, lock: ToolLock, name: str, url: str, bearer_env: str, replace: bool
    ) -> ToolLockAddition:
        self.remote_calls.append((lock, name, url, bearer_env, replace))
        if self.fail:
            raise self.fail
        entry = remote_server(name, url, bearer_env)
        inspection = McpServerInspection(
            McpServerInfo("docs-server", "2.0.0", "p"), McpToolSet(self.tools)
        )
        return ToolLockAddition(lock.with_server(entry, replace), entry, inspection)

    def grant(self, lock: ToolLock, name: str, stage: str, tools: tuple[str, ...]) -> ToolLock:
        self.edits.append(("grant", name, stage, tools))
        if self.fail:
            raise self.fail
        return lock.with_server((lock.server(name) or server(name)).with_grants(stage, tools), True)

    def revoke(self, lock: ToolLock, name: str, stage: str, tools: tuple[str, ...]) -> ToolLock:
        self.edits.append(("revoke", name, stage, tools))
        if self.fail:
            raise self.fail
        return lock.with_server(
            (lock.server(name) or server(name)).without_grants(stage, tools), True
        )


class Auditor(ToolLockAuditorInterface):
    def __init__(
        self, problems: dict[str, tuple[str, ...]] | None = None, fail: BaseException | None = None
    ) -> None:
        self.problems = problems or {}
        self.fail = fail
        self.asked: list[tuple[ToolLock, tuple[str, ...]]] = []

    def audit(self, lock: ToolLock, only: Collection[str]) -> tuple[ToolLockFinding, ...]:
        self.asked.append((lock, tuple(only)))
        if self.fail:
            raise self.fail
        return tuple(
            ToolLockFinding(s.name, self.problems.get(s.name, ()))
            for s in lock.servers
            if not only or s.name in only
        )


def cli(
    store: Store | None = None,
    editor: Editor | None = None,
    auditor: Auditor | None = None,
    environment: Mapping[str, str] | None = None,
):
    made = (store or Store(), editor or Editor(), auditor or Auditor())
    return ToolsCli(made[1], made[2], made[0], environment or {}), *made


def run(tools: ToolsCli, *argv: str) -> int:
    parser = argparse.ArgumentParser(prog="ei")
    tools.register(parser.add_subparsers(dest="command"))
    return tools.run(parser.parse_args(["tools", *argv]))


def test_it_is_a_tools_cli() -> None:
    assert isinstance(cli()[0], ToolsCliInterface)


# ------------------------------------------------------------------------------- the lock path
def test_the_lock_is_the_flag_then_the_environment_then_the_default_file() -> None:
    for environment, flags, expected in (
        ({}, ["--lock", "/x/flag.toml"], "/x/flag.toml"),
        ({"EI_TOOL_LOCK": "/x/env.toml"}, [], "/x/env.toml"),
        ({"EI_TOOL_LOCK": "  "}, [], "ei-tools.lock.toml"),
        ({}, [], "ei-tools.lock.toml"),
        ({"EI_TOOL_LOCK": "/x/env.toml"}, ["--lock", "/x/flag.toml"], "/x/flag.toml"),
    ):
        tools, store, _, _ = cli(environment=environment)
        run(tools, "list", *flags)
        assert store.loaded == [Path(expected)]


# ----------------------------------------------------------------------------------- add
def test_add_locks_the_server_saves_the_lock_and_shows_what_to_review(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tools, store, editor, _ = cli()
    status = run(
        tools,
        "add",
        "--lock",
        "/tmp/l.toml",
        "--env",
        "FILES_ROOT",
        "--env",
        "TOKEN",
        "files",
        "--",
        "node",
        "/opt/x.js",
        "--flag",
    )
    out = capsys.readouterr().out
    assert status == 0
    assert editor.calls == [
        (ToolLock(), "files", ("node", "/opt/x.js", "--flag"), ("FILES_ROOT", "TOKEN"), False)
    ]
    assert [path for path, _ in store.saved] == [Path("/tmp/l.toml")]
    assert store.saved[0][1].names() == ("files",)
    assert "locked files: files-server 1.2.0, 1 tools" in out
    assert "files locked: /opt/x.js, /usr/bin/node" in out
    assert (
        "tools (their descriptions are written by the server: read them before you commit this lock):"
        in out
    )
    assert "  read: Reads a file." in out
    assert "wrote /tmp/l.toml; review the change like any other commit" in out


def test_add_works_on_the_lock_that_is_there_and_passes_replace_on() -> None:
    existing = ToolLock((server("other"),))
    tools, store, editor, _ = cli(Store(existing))
    assert run(tools, "add", "--replace", "files", "--", "node") == 0
    assert editor.calls[0][0] is existing and editor.calls[0][4] is True
    assert store.saved[0][1].names() == ("files", "other")


def test_a_command_without_the_double_dash_is_still_a_command() -> None:
    tools, _, editor, _ = cli()
    assert run(tools, "add", "files", "node", "/opt/x.js") == 0
    assert editor.calls[0][2] == ("node", "/opt/x.js")


def test_a_missing_command_is_a_setup_error(capsys: pytest.CaptureFixture[str]) -> None:
    tools, store, editor, _ = cli()
    assert run(tools, "add", "files", "--") == 2
    assert "say the command to run, after --" in capsys.readouterr().err
    assert editor.calls == [] and store.saved == []


def test_a_refusal_is_a_setup_error_and_nothing_is_saved(
    capsys: pytest.CaptureFixture[str],
) -> None:
    refusal = ApplicationError(
        code="TOOL_COMMAND_REFUSED", message="npx fetches code", http_status=422
    )
    tools, store, _, _ = cli(editor=Editor(fail=refusal))
    assert run(tools, "add", "files", "--", "npx", "x") == 2
    assert "error: npx fetches code" in capsys.readouterr().err
    assert store.saved == []


def test_an_unreadable_lock_is_a_setup_error(capsys: pytest.CaptureFixture[str]) -> None:
    bad = ApplicationError(
        code="TOOL_LOCK_INVALID", message="lock.toml is not valid TOML", http_status=422
    )
    tools, _, editor, _ = cli(Store(fail=bad))
    assert run(tools, "add", "files", "--", "node") == 2
    assert "not valid TOML" in capsys.readouterr().err and editor.calls == []


def test_a_lock_that_cannot_be_written_is_a_setup_error_not_a_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    class Unwritable(Store):
        def save(self, path: Path, lock: ToolLock) -> None:
            raise PermissionError(13, "Permission denied")

    tools = ToolsCli(Editor(), Auditor(), Unwritable(), {})
    assert run(tools, "add", "files", "--", "node") == 2
    assert "error: Permission denied" in capsys.readouterr().err


def test_an_oserror_with_no_message_still_names_its_type(
    capsys: pytest.CaptureFixture[str],
) -> None:
    class Odd(Store):
        def load(self, path: Path) -> ToolLock | None:
            raise OSError()

    assert run(ToolsCli(Editor(), Auditor(), Odd(), {}), "list") == 2
    assert "error: OSError" in capsys.readouterr().err


def test_what_a_server_called_itself_and_its_tools_is_printed_safely(
    capsys: pytest.CaptureFixture[str],
) -> None:
    nasty = McpToolDescriptor(
        "tricky", "\x1b[31mred\x1b[0m\rtext " + "long " * 60, {"type": "object"}
    )
    quiet = McpToolDescriptor("quiet", "", {"type": "object"})
    tools, _, _, _ = cli(editor=Editor((nasty, quiet)))
    assert run(tools, "add", "files", "--", "node") == 0
    out = capsys.readouterr().out
    assert "\x1b" not in out and "\r" not in out
    assert "  quiet: (no description)" in out
    line = next(line for line in out.splitlines() if line.startswith("  tricky:"))
    assert len(line) < 130 and line.endswith("…")


def test_tools_that_cannot_be_offered_are_counted(capsys: pytest.CaptureFixture[str]) -> None:
    odd = McpToolDescriptor("odd tool", "A name no provider accepts.", {"type": "object"})
    tools, _, _, _ = cli(editor=Editor((odd, McpToolDescriptor("fine", "Ok.", {"type": "object"}))))
    run(tools, "add", "files", "--", "node")
    assert "2 tools, 1 that cannot be offered under that name" in capsys.readouterr().out


# ---------------------------------------------------------------------------------- list
def test_list_with_no_lock_file_says_so(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(cli()[0], "list", "--lock", "/x/none.toml") == 0
    assert capsys.readouterr().out == "no tool lock at /x/none.toml\n"


def test_list_with_an_empty_lock_says_so(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(cli(Store(ToolLock()))[0], "list", "--lock", "/x/l.toml") == 0
    assert capsys.readouterr().out == "/x/l.toml locks no servers\n"


def test_list_shows_each_server_in_name_order_and_starts_nothing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    lock = ToolLock(
        (
            server("zed", env=("FILES_ROOT", "TOKEN"), server_name="z\x1b[31m-server"),
            server("alpha"),
        )
    )
    tools, _, editor, auditor = cli(Store(lock))
    assert run(tools, "list") == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines == [
        "alpha  files-server 1.2.0  1 tools",
        "    /usr/bin/node /opt/x.js",
        "zed  z [31m-server 1.2.0  1 tools",
        "    /usr/bin/node /opt/x.js",
        "    env: FILES_ROOT TOKEN",
    ]
    assert editor.calls == [] and auditor.asked == []


# --------------------------------------------------------------------------------- verify
def test_verify_with_no_lock_file_is_a_setup_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(cli()[0], "verify", "--lock", "/x/none.toml") == 2
    assert "error: no tool lock at /x/none.toml" in capsys.readouterr().err


def test_verify_with_an_empty_lock_has_nothing_to_do(capsys: pytest.CaptureFixture[str]) -> None:
    tools, _, _, auditor = cli(Store(ToolLock()))
    assert run(tools, "verify") == 0
    assert "locks no servers; nothing to verify" in capsys.readouterr().out
    assert auditor.asked == []


def test_verify_says_it_starts_each_server_and_passes_when_all_match(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tools, _, _, auditor = cli(Store(ToolLock((server("a"), server("b")))))
    assert run(tools, "verify") == 0
    out = capsys.readouterr().out
    assert out.splitlines() == [
        "starting each locked server to compare what it reports with the lock",
        "ok    a",
        "ok    b",
        "all 2 servers match the lock",
    ]
    assert auditor.asked[0][1] == ()


def test_verify_fails_with_status_one_and_shows_each_problem(
    capsys: pytest.CaptureFixture[str],
) -> None:
    auditor = Auditor(
        {"b": ("/x has changed since it was locked", "the server is now version '2'")}
    )
    tools, _, _, _ = cli(Store(ToolLock((server("a"), server("b")))), auditor=auditor)
    assert run(tools, "verify") == 1
    out = capsys.readouterr().out
    assert "ok    a" in out
    assert (
        "FAIL  b: /x has changed since it was locked" in out
        and "FAIL  b: the server is now version '2'" in out
    )
    assert "1 of 2 servers no longer match the lock" in out


def test_verify_passes_the_names_on(capsys: pytest.CaptureFixture[str]) -> None:
    tools, _, _, auditor = cli(Store(ToolLock((server("a"), server("b")))))
    assert run(tools, "verify", "b") == 0
    assert auditor.asked[0][1] == ("b",)
    assert "all 1 servers match" in capsys.readouterr().out


def test_verify_with_an_unknown_name_is_a_setup_error(capsys: pytest.CaptureFixture[str]) -> None:
    tools, _, _, _ = cli(
        Store(ToolLock((server("a"),))),
        auditor=Auditor(fail=ValueError("no server named 'nope' is locked")),
    )
    assert run(tools, "verify", "nope") == 2
    assert "error: no server named 'nope' is locked" in capsys.readouterr().err


@pytest.mark.parametrize("late", [["--lock", "/x/l.toml"], ["--env", "TOKEN"], ["--replace"]])
def test_an_option_placed_after_the_name_gets_a_clear_error_and_nothing_runs(
    late: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    tools, store, editor, _ = cli()
    assert run(tools, "add", "files", *late, "--", "node") == 2
    assert "error: options go before the name:" in capsys.readouterr().err
    assert editor.calls == [] and store.saved == []


def namespace(*server_command: str) -> argparse.Namespace:
    """What the parser hands over, built by hand: whether argparse keeps the -- differs by version."""
    return argparse.Namespace(
        tools_command="add",
        lock=Path("/x/l.toml"),
        name="files",
        env=[],
        url=None,
        bearer_env="",
        replace=False,
        server_command=list(server_command),
    )


def test_a_double_dash_that_the_parser_kept_is_dropped_before_the_command() -> None:
    tools, _, editor, _ = cli()
    assert tools.run(namespace("--", "node", "/opt/x.js")) == 0
    assert editor.calls[0][2] == ("node", "/opt/x.js")


def test_a_double_dash_alone_is_still_a_missing_command(capsys: pytest.CaptureFixture[str]) -> None:
    tools, _, editor, _ = cli()
    assert tools.run(namespace("--")) == 2
    assert "say the command to run, after --" in capsys.readouterr().err and editor.calls == []


def test_a_command_that_starts_with_dashes_after_the_double_dash_is_a_command() -> None:
    tools, _, editor, _ = cli()
    assert tools.run(namespace("--", "--odd-name")) == 0
    assert editor.calls[0][2] == ("--odd-name",)


def test_text_of_exactly_the_limit_is_shown_whole_and_one_over_is_cut(
    capsys: pytest.CaptureFixture[str],
) -> None:
    whole = McpToolDescriptor("exact", "x" * ToolsCli.SHOWN, {"type": "object"})
    over = McpToolDescriptor("over", "y" * (ToolsCli.SHOWN + 1), {"type": "object"})
    tools, _, _, _ = cli(editor=Editor((whole, over)))
    run(tools, "add", "files", "--", "node")
    lines = {
        line.split(":")[0].strip(): line.split(": ", 1)[1]
        for line in capsys.readouterr().out.splitlines()
        if line.startswith("  ")
    }
    assert lines["exact"] == "x" * ToolsCli.SHOWN
    assert lines["over"] == "y" * (ToolsCli.SHOWN - 1) + "…"


# ---------------------------------------------------------------------------- grant and revoke
def granted_lock() -> ToolLock:
    return ToolLock((server("files").with_grants("research", ("read",)),))


def test_grant_lets_a_stage_call_a_tool_saves_the_lock_and_says_to_review_it(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tools, store, editor, _ = cli(Store(ToolLock((server("files"),))))
    assert run(tools, "grant", "--lock", "/x/l.toml", "files", "research", "read") == 0
    out = capsys.readouterr().out
    assert editor.edits == [("grant", "files", "research", ("read",))]
    assert store.saved[0][0] == Path("/x/l.toml")
    saved = store.saved[0][1].server("files")
    assert saved is not None and saved.granted("research") == ("read",)
    assert "granted files read to stage research" in out
    assert "wrote /x/l.toml; review the change like any other commit" in out


def test_grant_needs_at_least_one_tool() -> None:
    with pytest.raises(SystemExit):
        run(cli()[0], "grant", "files", "research")


def test_grant_with_no_lock_file_is_a_setup_error(capsys: pytest.CaptureFixture[str]) -> None:
    tools, store, editor, _ = cli()
    assert run(tools, "grant", "--lock", "/x/none.toml", "files", "research", "read") == 2
    assert "error: no tool lock at /x/none.toml" in capsys.readouterr().err
    assert editor.edits == [] and store.saved == []


def test_a_grant_the_editor_refuses_is_a_setup_error_and_nothing_is_saved(
    capsys: pytest.CaptureFixture[str],
) -> None:
    refusal = ApplicationError(
        code="TOOL_GRANT_INVALID", message="'delete' is not listed", http_status=422
    )
    tools, store, _, _ = cli(Store(ToolLock((server("files"),))), editor=Editor(fail=refusal))
    assert run(tools, "grant", "files", "research", "delete") == 2
    assert "error: 'delete' is not listed" in capsys.readouterr().err
    assert store.saved == []


def test_revoke_takes_named_tools_back_and_saves(capsys: pytest.CaptureFixture[str]) -> None:
    tools, store, editor, _ = cli(Store(granted_lock()))
    assert run(tools, "revoke", "files", "research", "read") == 0
    assert editor.edits == [("revoke", "files", "research", ("read",))]
    saved = store.saved[0][1].server("files")
    assert saved is not None and saved.grants == ()
    assert "took read of files from stage research" in capsys.readouterr().out


def test_revoke_naming_no_tool_takes_them_all(capsys: pytest.CaptureFixture[str]) -> None:
    tools, _, editor, _ = cli(Store(granted_lock()))
    assert run(tools, "revoke", "files", "research") == 0
    assert editor.edits == [("revoke", "files", "research", ())]
    assert "took all the tools of files from stage research" in capsys.readouterr().out


def test_revoke_with_no_lock_file_is_a_setup_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(cli()[0], "revoke", "files", "research") == 2
    assert "no tool lock at" in capsys.readouterr().err


def test_list_shows_what_each_stage_may_call(capsys: pytest.CaptureFixture[str]) -> None:
    entry = server("files").with_grants("outline", ("read",)).with_grants("research", ("read",))
    assert run(cli(Store(ToolLock((entry,))))[0], "list") == 0
    lines = capsys.readouterr().out.splitlines()
    assert "    outline may call: read" in lines and "    research may call: read" in lines
    assert lines.index("    outline may call: read") < lines.index("    research may call: read")


# ------------------------------------------------------------------------------ a remote server
def test_add_with_an_address_contacts_it_and_shows_that_only_the_address_is_locked(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tools, store, editor, _ = cli()
    status = run(
        tools,
        "add",
        "--lock",
        "/tmp/l.toml",
        "--bearer-env",
        "DOCS_TOKEN",
        "--url",
        "https://mcp.example.com/mcp",
        "docs",
    )
    out = capsys.readouterr().out
    assert status == 0 and editor.calls == []
    assert editor.remote_calls == [
        (ToolLock(), "docs", "https://mcp.example.com/mcp", "DOCS_TOKEN", False)
    ]
    assert store.saved[0][1].names() == ("docs",)
    assert "locked docs: docs-server 2.0.0, 1 tools" in out
    assert (
        "address locked: https://mcp.example.com/mcp "
        "(its code is not locked: only the address and what it advertises are)"
    ) in out
    assert "files locked" not in out


def test_add_with_an_address_works_on_the_lock_that_is_there_and_passes_replace_on() -> None:
    existing = ToolLock((server("other"),))
    tools, store, editor, _ = cli(Store(existing))
    assert run(tools, "add", "--replace", "--url", "https://mcp.example.com/mcp", "docs") == 0
    assert editor.remote_calls[0][0] is existing and editor.remote_calls[0][4] is True
    assert editor.remote_calls[0][3] == ""
    assert store.saved[0][1].names() == ("docs", "other")


def test_an_address_and_a_command_together_are_a_setup_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tools, store, editor, _ = cli()
    assert run(tools, "add", "--url", "https://mcp.example.com/mcp", "docs", "--", "node") == 2
    assert "takes no command and no --env" in capsys.readouterr().err
    assert editor.remote_calls == [] and store.saved == []


def test_an_address_and_env_variables_together_are_a_setup_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tools, store, editor, _ = cli()
    assert run(tools, "add", "--url", "https://mcp.example.com/mcp", "--env", "X", "docs") == 2
    assert "takes no command and no --env" in capsys.readouterr().err
    assert editor.remote_calls == [] and store.saved == []


def test_a_bearer_variable_without_an_address_is_a_setup_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tools, store, editor, _ = cli()
    assert run(tools, "add", "--bearer-env", "TOKEN", "files", "--", "node") == 2
    assert "--bearer-env goes with --url" in capsys.readouterr().err
    assert editor.calls == [] and store.saved == []


def test_a_remote_refusal_is_a_setup_error_and_nothing_is_saved(
    capsys: pytest.CaptureFixture[str],
) -> None:
    refusal = ApplicationError(code="TOOL_URL_REFUSED", message="plain http", http_status=422)
    tools, store, _, _ = cli(editor=Editor(fail=refusal))
    assert run(tools, "add", "--url", "http://x.example/mcp", "docs") == 2
    assert "error: plain http" in capsys.readouterr().err and store.saved == []


def test_list_shows_a_remote_server_by_its_address_and_bearer_variable(
    capsys: pytest.CaptureFixture[str],
) -> None:
    lock = ToolLock((remote_server(bearer_env="DOCS_TOKEN"), server("files", env=("ROOT",))))
    tools, _, _, _ = cli(Store(lock))
    assert run(tools, "list") == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("docs  docs-server 2.0.0  1 tools")
    assert lines[1:3] == ["    url: https://mcp.example.com/mcp", "    bearer: DOCS_TOKEN"]
    assert "    /usr/bin/node /opt/x.js" in lines and "    env: ROOT" in lines


def test_list_shows_a_remote_server_that_needs_no_token_without_a_bearer_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tools, _, _, _ = cli(Store(ToolLock((remote_server(),))))
    assert run(tools, "list") == 0
    assert "bearer" not in capsys.readouterr().out
