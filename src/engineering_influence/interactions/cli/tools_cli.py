# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ``tools`` command: lock, list and check third-party tool servers."""

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.cli.interfaces.tools_cli_interface import ToolsCliInterface
from engineering_influence.interfaces.tool_lock_store_interface import ToolLockStoreInterface
from engineering_influence.models.tool_lock import ToolLock
from engineering_influence.models.tool_lock_addition import ToolLockAddition
from engineering_influence.services.interfaces.tool_lock_auditor_interface import (
    ToolLockAuditorInterface,
)
from engineering_influence.services.interfaces.tool_lock_editor_interface import (
    ToolLockEditorInterface,
)


class ToolsCli(ToolsCliInterface):
    """``tools add`` runs a server once and records it, ``tools list`` reads the lock, ``tools verify`` runs each locked server and compares.

    Exit 0 when all held, 1 when a server no longer matches its lock, 2 on setup trouble (an
    unreadable lock, a refused command, an unknown name). The lock is ``--lock``, or ``EI_TOOL_LOCK``,
    or ``ei-tools.lock.toml`` in the current directory. ``add`` and ``verify`` **start the server's
    code**, under limits and with a bare environment; ``list`` starts nothing. Everything a server
    said is printed with control characters replaced and long text cut, because it is untrusted.
    """

    DEFAULT_LOCK = "ei-tools.lock.toml"
    SHOWN = 100

    def __init__(
        self,
        editor: ToolLockEditorInterface,
        auditor: ToolLockAuditorInterface,
        store: ToolLockStoreInterface,
        environment: Mapping[str, str],
    ) -> None:
        self._editor = editor
        self._auditor = auditor
        self._store = store
        self._environment = environment

    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``tools add``, ``tools list`` and ``tools verify`` to the command line."""
        tools = subparsers.add_parser("tools", help="lock, list and check third-party tool servers")
        commands = tools.add_subparsers(dest="tools_command", required=True)
        add = commands.add_parser(
            "add",
            usage="ei tools add [--lock PATH] [--env VAR] [--replace] NAME -- COMMAND [ARG...]",
            help="run an MCP server once and lock what it is (options go before NAME)",
        )
        add.add_argument("name", help="the server's name in the lock")
        add.add_argument("--lock", type=Path, help="default: EI_TOOL_LOCK or ei-tools.lock.toml")
        add.add_argument(
            "--env", action="append", default=[], metavar="VAR", help="pass this variable on"
        )
        add.add_argument(
            "--replace", action="store_true", help="lock a server that is already locked again"
        )
        add.add_argument(
            "server_command",
            nargs=argparse.REMAINDER,
            metavar="COMMAND",
            help="after --: the command to run",
        )
        listing = commands.add_parser("list", help="show the locked servers (starts nothing)")
        listing.add_argument(
            "--lock", type=Path, help="default: EI_TOOL_LOCK or ei-tools.lock.toml"
        )
        verify = commands.add_parser(
            "verify", help="run each locked server and compare it with the lock"
        )
        verify.add_argument("--lock", type=Path, help="default: EI_TOOL_LOCK or ei-tools.lock.toml")
        verify.add_argument("names", nargs="*", help="only these servers")

    def run(self, arguments: argparse.Namespace) -> int:
        """Run the chosen subcommand and return the exit status."""
        path = arguments.lock or Path(
            self._environment.get("EI_TOOL_LOCK", "").strip() or self.DEFAULT_LOCK
        )
        try:
            if arguments.tools_command == "add":
                return self._add(arguments, path)
            if arguments.tools_command == "list":
                return self._list(path)
            return self._verify(arguments, path)
        except (ApplicationError, ValueError) as error:
            print(
                f"error: {self._safe(getattr(error, 'message', str(error)), 400)}", file=sys.stderr
            )
            return 2
        except OSError as error:
            print(f"error: {error.strerror or type(error).__name__}", file=sys.stderr)
            return 2

    def _add(self, arguments: argparse.Namespace, path: Path) -> int:
        given = list(arguments.server_command)
        if given and given[0] != "--" and given[0].startswith("-"):
            print(
                "error: options go before the name: "
                "ei tools add [--lock PATH] [--env VAR] [--replace] NAME -- COMMAND [ARG...]",
                file=sys.stderr,
            )
            return 2
        command = tuple(given[1:] if given[:1] == ["--"] else given)
        if not command:
            print("error: say the command to run, after --", file=sys.stderr)
            return 2
        lock = self._store.load(path) or ToolLock()
        added = self._editor.add(
            lock, arguments.name, command, tuple(arguments.env), arguments.replace
        )
        self._store.save(path, added.lock)
        self._show(path, added)
        return 0

    def _show(self, path: Path, added: ToolLockAddition) -> None:
        server, inspection = added.server, added.inspection
        skipped = inspection.tools.skipped(server.name)
        extra = f", {len(skipped)} that cannot be offered under that name" if skipped else ""
        print(
            f"locked {server.name}: {self._safe(server.server_name)} {self._safe(server.server_version)}, "
            f"{len(inspection.tools.tools)} tools{extra}"
        )
        print("files locked: " + ", ".join(file for file, _ in server.files))
        print(
            "tools (their descriptions are written by the server: read them before you commit this lock):"
        )
        for tool in sorted(inspection.tools.tools, key=lambda found: found.name):
            print(
                f"  {self._safe(tool.name, 60)}: {self._safe(tool.description, self.SHOWN) or '(no description)'}"
            )
        print(f"wrote {path}; review the change like any other commit")

    def _list(self, path: Path) -> int:
        lock = self._store.load(path)
        if lock is None:
            print(f"no tool lock at {path}")
            return 0
        if not lock.servers:
            print(f"{path} locks no servers")
            return 0
        for server in sorted(lock.servers, key=lambda found: found.name):
            print(
                f"{server.name}  {self._safe(server.server_name)} {self._safe(server.server_version)}  "
                f"{len(server.tool_names)} tools"
            )
            print("    " + self._safe(" ".join(server.command), 300))
            if server.env:
                print("    env: " + " ".join(server.env))
        return 0

    def _verify(self, arguments: argparse.Namespace, path: Path) -> int:
        lock = self._store.load(path)
        if lock is None:
            print(f"error: no tool lock at {path}", file=sys.stderr)
            return 2
        if not lock.servers:
            print(f"{path} locks no servers; nothing to verify")
            return 0
        print("starting each locked server to compare what it reports with the lock")
        findings = self._auditor.audit(lock, tuple(arguments.names))
        for finding in findings:
            for line in finding.lines():
                print(line)
        failed = sum(1 for finding in findings if not finding.passed())
        if failed:
            print(f"{failed} of {len(findings)} servers no longer match the lock")
            return 1
        print(f"all {len(findings)} servers match the lock")
        return 0

    @staticmethod
    def _safe(text: str, limit: int = 100) -> str:
        """Untrusted text on one line: anything not printable becomes a space, and long text is cut."""
        flat = " ".join("".join(c if c.isprintable() else " " for c in text).split())
        return flat if len(flat) <= limit else flat[: limit - 1] + "…"
