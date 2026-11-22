# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ``skills`` command: install, enable, list and check prompt skills."""

import argparse
import sys
from collections.abc import Mapping
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.cli.interfaces.skills_cli_interface import (
    SkillsCliInterface,
)
from engineering_influence.interfaces.skill_lock_store_interface import SkillLockStoreInterface
from engineering_influence.models.skill_lock import SkillLock
from engineering_influence.models.skill_lock_addition import SkillLockAddition
from engineering_influence.services.interfaces.skill_lock_editor_interface import (
    SkillLockEditorInterface,
)
from engineering_influence.services.interfaces.skill_lock_verifier_interface import (
    SkillLockVerifierInterface,
)


class SkillsCli(SkillsCliInterface):
    """``skills add`` locks a file, ``enable`` and ``disable`` choose its stages, ``list`` reads the lock, ``verify`` re-hashes each file.

    Exit 0 when all held, 1 when a skill no longer matches its lock, 2 on setup trouble (an
    unreadable lock or file, an unknown name or stage). The lock is ``--lock``, or ``EI_SKILL_LOCK``,
    or ``ei-skills.lock.toml`` in the current directory, and the skills are kept in ``skills/``
    beside it. Nothing here starts a process or opens a connection; a skill is text. What a skill
    says is still untrusted, so it is printed with control characters replaced and long text cut.
    """

    DEFAULT_LOCK = "ei-skills.lock.toml"
    SHOWN = 100

    def __init__(
        self,
        editor: SkillLockEditorInterface,
        verifier: SkillLockVerifierInterface,
        store: SkillLockStoreInterface,
        environment: Mapping[str, str],
    ) -> None:
        self._editor = editor
        self._verifier = verifier
        self._store = store
        self._environment = environment

    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``skills add``, ``enable``, ``disable``, ``remove``, ``list`` and ``verify``."""
        skills = subparsers.add_parser("skills", help="install, enable and check prompt skills")
        commands = skills.add_subparsers(dest="skills_command", required=True)
        where = "default: EI_SKILL_LOCK or ei-skills.lock.toml"
        add = commands.add_parser(
            "add", help="lock a skill file and keep a copy beside the lock (enables nothing)"
        )
        add.add_argument("--lock", type=Path, help=where)
        add.add_argument(
            "--replace", action="store_true", help="lock a skill that is already locked again"
        )
        add.add_argument("file", type=Path, help="the skill file, for example plain_style.toml")
        for command, help_text in (
            ("enable", "let a stage's prompt carry a skill"),
            ("disable", "stop a stage's prompt carrying a skill"),
        ):
            changing = commands.add_parser(command, help=help_text)
            changing.add_argument("--lock", type=Path, help=where)
            changing.add_argument("name", help="the locked skill")
            changing.add_argument("stage", help="the stage, for example outline")
        remove = commands.add_parser("remove", help="unlock a skill and delete its copy")
        remove.add_argument("--lock", type=Path, help=where)
        remove.add_argument("name", help="the locked skill")
        listing = commands.add_parser("list", help="show the locked skills")
        listing.add_argument("--lock", type=Path, help=where)
        verify = commands.add_parser("verify", help="re-hash each locked skill against the lock")
        verify.add_argument("--lock", type=Path, help=where)

    def run(self, arguments: argparse.Namespace) -> int:
        """Run the chosen subcommand and return the exit status."""
        path = arguments.lock or Path(
            self._environment.get("EI_SKILL_LOCK", "").strip() or self.DEFAULT_LOCK
        )
        try:
            command = arguments.skills_command
            if command == "add":
                return self._add(arguments, path)
            if command == "list":
                return self._list(path)
            if command == "verify":
                return self._verify(path)
            return self._change(arguments, path)
        except (ApplicationError, ValueError) as error:
            print(
                f"error: {self._safe(getattr(error, 'message', str(error)), 400)}", file=sys.stderr
            )
            return 2
        except OSError as error:
            print(f"error: {error.strerror or type(error).__name__}", file=sys.stderr)
            return 2

    @staticmethod
    def _folder(path: Path) -> Path:
        return path.parent / "skills"

    def _add(self, arguments: argparse.Namespace, path: Path) -> int:
        lock = self._store.load(path) or SkillLock()
        added = self._editor.add(lock, self._folder(path), arguments.file, arguments.replace)
        self._store.save(path, added.lock)
        self._show(path, added)
        return 0

    def _show(self, path: Path, added: SkillLockAddition) -> None:
        skill = added.skill
        print(f"locked {skill.identifier()}: {len(skill.parts)} parts")
        if skill.description:
            print(f"  {self._safe(skill.description, self.SHOWN)}")
        print(
            "this text will be added to prompts, and it is written by whoever made the skill: "
            "read it before you commit this lock"
        )
        for stage, text in skill.parts:
            print(f"  {stage} ({len(text)} characters): {self._safe(text, self.SHOWN)}")
        print(f"copy kept at {self._folder(path) / (skill.name + '.toml')}")
        print(
            f"enabled for no stage yet: ei skills enable {skill.name} STAGE "
            f"(it has text for {', '.join(skill.stages())})"
        )
        print(f"wrote {path}; review the change like any other commit")

    def _change(self, arguments: argparse.Namespace, path: Path) -> int:
        lock = self._store.load(path)
        if lock is None:
            print(f"error: no skill lock at {path}", file=sys.stderr)
            return 2
        folder = self._folder(path)
        if arguments.skills_command == "enable":
            changed = self._editor.enable(lock, folder, arguments.name, arguments.stage)
            said = f"enabled {arguments.name} for stage {arguments.stage}"
        elif arguments.skills_command == "disable":
            changed = self._editor.disable(lock, arguments.name, arguments.stage)
            said = f"disabled {arguments.name} for stage {arguments.stage}"
        else:
            changed = self._editor.remove(lock, folder, arguments.name)
            said = f"removed {arguments.name} and its copy in {folder}"
        self._store.save(path, changed)
        print(self._safe(said, 300))
        print(f"wrote {path}; review the change like any other commit")
        return 0

    def _list(self, path: Path) -> int:
        lock = self._store.load(path)
        if lock is None:
            print(f"no skill lock at {path}")
            return 0
        if not lock.entries:
            print(f"{path} locks no skills")
            return 0
        for entry in sorted(lock.entries, key=lambda found: found.name):
            where = (
                "enabled for " + " ".join(entry.stages) if entry.stages else "enabled for no stage"
            )
            print(f"{entry.name}@{entry.version}  {entry.sha256[:12]}  {where}")
        return 0

    def _verify(self, path: Path) -> int:
        lock = self._store.load(path)
        if lock is None:
            print(f"error: no skill lock at {path}", file=sys.stderr)
            return 2
        if not lock.entries:
            print(f"{path} locks no skills; nothing to verify")
            return 0
        problems = self._verifier.problems(lock, self._folder(path))
        for problem in problems:
            print(self._safe(problem, 400))
        if problems:
            print(f"{len(problems)} of {len(lock.entries)} skills no longer match the lock")
            return 1
        print(f"all {len(lock.entries)} skills match the lock")
        return 0

    @staticmethod
    def _safe(text: str, limit: int = 100) -> str:
        """Untrusted text on one line: anything not printable becomes a space, and long text is cut."""
        flat = " ".join("".join(c if c.isprintable() else " " for c in text).split())
        return flat if len(flat) <= limit else flat[: limit - 1] + "…"
