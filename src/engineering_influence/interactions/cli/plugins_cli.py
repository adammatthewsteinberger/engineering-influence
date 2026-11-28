# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ``plugins`` command: look at, install, check and remove reviewed bundles."""

import argparse
import shlex
import sys
from collections.abc import Mapping
from pathlib import Path
from urllib.parse import urlsplit

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.cli.interfaces.plugins_cli_interface import (
    PluginsCliInterface,
)
from engineering_influence.interfaces.plugin_lock_store_interface import PluginLockStoreInterface
from engineering_influence.interfaces.skill_lock_store_interface import SkillLockStoreInterface
from engineering_influence.models.plugin_bundle import PluginBundle
from engineering_influence.models.plugin_lock import PluginLock
from engineering_influence.models.skill_lock import SkillLock
from engineering_influence.services.interfaces.plugin_importer_interface import (
    PluginImporterInterface,
)
from engineering_influence.services.interfaces.plugin_installer_interface import (
    PluginInstallerInterface,
)
from engineering_influence.services.interfaces.plugin_lock_verifier_interface import (
    PluginLockVerifierInterface,
)
from engineering_influence.services.interfaces.plugin_marketplace_interface import (
    PluginMarketplaceInterface,
)


class PluginsCli(PluginsCliInterface):
    """``plugins show`` reads a bundle, ``add`` installs its skills, ``list`` and ``verify`` check, ``remove`` undoes,
    and ``search`` and ``fetch`` read a marketplace index and download a plugin file from it.

    ``search`` and ``fetch`` are the only commands here that can use a network, and only for an ``https://``
    index or an https address an index lists. ``fetch`` checks the downloaded bytes against the index's hash
    before reading them, saves a file, and **installs nothing**: a person reads it and runs ``add``.

    **Nothing here starts a process, opens a connection, grants a tool or enables a skill for a
    stage.** ``add`` locks the bundle's skills (enabled for no stage) and records the bundle's hash; the
    servers it describes are *printed* as the ``ei tools add`` commands a person would run, because
    that command is the step that starts a server. Exit 0 when all held, 1 when a bundle or a skill
    no longer matches, 2 on setup trouble. The plugin lock is ``--lock``, or ``EI_PLUGIN_LOCK``, or
    ``ei-plugins.lock.toml`` in the current directory, with the bundles kept in ``plugins/`` beside it;
    the skill lock is ``--skill-lock``, or ``EI_SKILL_LOCK``, or ``ei-skills.lock.toml``. Everything a
    bundle says is untrusted, so it is printed with control characters replaced and long text cut,
    except the commands, whose parts the model has already limited to printable text.
    """

    DEFAULT_LOCK = "ei-plugins.lock.toml"
    DEFAULT_SKILL_LOCK = "ei-skills.lock.toml"
    SHOWN = 100

    def __init__(
        self,
        installer: PluginInstallerInterface,
        importer: PluginImporterInterface,
        verifier: PluginLockVerifierInterface,
        marketplace: PluginMarketplaceInterface,
        store: PluginLockStoreInterface,
        skill_store: SkillLockStoreInterface,
        environment: Mapping[str, str],
    ) -> None:
        """Remember the installer, importer, verifier and marketplace the plugin commands use."""
        self._installer = installer
        self._importer = importer
        self._verifier = verifier
        self._marketplace = marketplace
        self._store = store
        self._skill_store = skill_store
        self._environment = environment

    def register(self, subparsers: "argparse._SubParsersAction[argparse.ArgumentParser]") -> None:
        """Add ``plugins show``, ``add``, ``list``, ``verify`` and ``remove`` to the command line."""
        plugins = subparsers.add_parser(
            "plugins", help="look at, install, check and remove reviewed plugin bundles"
        )
        commands = plugins.add_subparsers(dest="plugins_command", required=True)
        where = "default: EI_PLUGIN_LOCK or ei-plugins.lock.toml"
        skills = "default: EI_SKILL_LOCK or ei-skills.lock.toml"
        show = commands.add_parser(
            "show", help="read a plugin file and say what installing it would do"
        )
        show.add_argument("file", type=Path, help="the plugin file, for example research_pack.toml")
        convert = commands.add_parser(
            "import",
            help="turn a Claude Code plugin folder into a bundle to review, then install it with add (installs and runs nothing)",
        )
        convert.add_argument("source", type=Path, help="the plugin's folder")
        convert.add_argument("--name", help="the bundle's name; default: the plugin's, made safe")
        convert.add_argument(
            "--version", type=int, default=1, help="the bundle's version, default 1"
        )
        convert.add_argument("--out", type=Path, help="where to write it; default NAME.toml here")
        add = commands.add_parser(
            "add", help="lock a plugin's skills and record its hash (runs and contacts nothing)"
        )
        add.add_argument("--lock", type=Path, help=where)
        add.add_argument("--skill-lock", type=Path, help=skills)
        add.add_argument("file", type=Path, help="the plugin file, for example research_pack.toml")
        search = commands.add_parser(
            "search",
            help="list the plugins in a marketplace: an index (TOML) or a Claude Code marketplace.json, a file or an https address",
        )
        search.add_argument("index", help="a file on disk or an https:// address")
        search.add_argument(
            "text", nargs="?", default="", help="only plugins whose name or description has this"
        )
        fetch = commands.add_parser(
            "fetch",
            help="download a plugin file from an index, checked against its hash (installs nothing)",
        )
        fetch.add_argument("index", help="a file on disk or an https:// address")
        fetch.add_argument("name", help="the plugin's name in the index")
        fetch.add_argument(
            "--output",
            type=Path,
            default=Path("."),
            help="the folder to save it in (default: here)",
        )
        listing = commands.add_parser("list", help="show the installed plugins")
        listing.add_argument("--lock", type=Path, help=where)
        verify = commands.add_parser("verify", help="re-hash each installed plugin and its skills")
        verify.add_argument("--lock", type=Path, help=where)
        verify.add_argument("--skill-lock", type=Path, help=skills)
        remove = commands.add_parser(
            "remove", help="uninstall a plugin and the skills it installed"
        )
        remove.add_argument("--lock", type=Path, help=where)
        remove.add_argument("--skill-lock", type=Path, help=skills)
        remove.add_argument("name", help="the installed plugin")

    def run(self, arguments: argparse.Namespace) -> int:
        """Run the chosen subcommand and return the exit status."""
        command = arguments.plugins_command
        try:
            if command == "show":
                self._describe(self._installer.inspect(arguments.file), "")
                return 0
            if command == "import":
                return self._import(arguments)
            if command == "search":
                return self._search(arguments.index, arguments.text)
            if command == "fetch":
                return self._fetch(arguments)
            path = arguments.lock or Path(
                self._environment.get("EI_PLUGIN_LOCK", "").strip() or self.DEFAULT_LOCK
            )
            if command == "list":
                return self._list(path)
            skill_path = arguments.skill_lock or Path(
                self._environment.get("EI_SKILL_LOCK", "").strip() or self.DEFAULT_SKILL_LOCK
            )
            if command == "add":
                return self._add(arguments, path, skill_path)
            if command == "verify":
                return self._verify(path, skill_path)
            return self._remove(arguments, path, skill_path)
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
        return path.parent / "plugins"

    @staticmethod
    def _skill_folder(path: Path) -> Path:
        return path.parent / "skills"

    def _import(self, arguments: argparse.Namespace) -> int:
        done = self._importer.import_plugin(
            arguments.source, arguments.name, arguments.version, arguments.out
        )
        conversion = done.conversion
        plugin = conversion.plugin
        print(f"wrote {self._safe(done.path, 200)}: {plugin.identifier()}")
        for skill in plugin.skills:
            print(
                f"  skill {skill.name}: {len(skill.sections)} reference sections, "
                f"{sum(len(text) for _, text in skill.sections):,} characters"
            )
        for server in plugin.servers:
            how = "address" if server.remote() else "command"
            print(f"  server {server.name}: {how}")
        for what, why in conversion.skipped:
            print(f"  skipped {self._safe(what, 100)}: {self._safe(why, 300)}")
        for note in conversion.notes:
            print(f"  note: {self._safe(note, 300)}")
        for line in conversion.set_aside:
            print(f"  set aside: {self._safe(line, 200)}")
        print(
            "this bundle's text will be added to prompts and its servers would be started, "
            "and it was written by whoever made the plugin: read the file before you install it"
        )
        print(f"then: ei plugins show {self._safe(done.path, 200)}")
        return 0

    def _add(self, arguments: argparse.Namespace, path: Path, skill_path: Path) -> int:
        plugins = self._store.load(path) or PluginLock()
        skills = self._skill_store.load(skill_path) or SkillLock()
        added = self._installer.add(
            plugins, skills, self._folder(path), self._skill_folder(skill_path), arguments.file
        )
        self._skill_store.save(skill_path, added.skills)
        self._store.save(path, added.lock)
        self._describe(added.bundle, "installed ")
        print(f"wrote {skill_path} and {path}; review the change like any other commit")
        return 0

    def _describe(self, bundle: PluginBundle, verb: str) -> None:
        plugin = bundle.plugin
        print(
            f"{verb}{plugin.identifier()} (bundle sha256 {bundle.sha256[:12]}): "
            f"{len(plugin.servers)} servers, {len(plugin.skills)} skills"
        )
        if plugin.description:
            print(f"  {self._safe(plugin.description, self.SHOWN)}")
        if plugin.skills:
            print(
                "skills: text that will be added to prompts once you enable it for a stage, "
                "and it is written by whoever made the plugin: read it first"
            )
            for skill in plugin.skills:
                print(f"  {skill.identifier()}, text for {', '.join(skill.stages())}")
                for stage, text in skill.parts:
                    print(f"    {stage} ({len(text)} characters): {self._safe(text, self.SHOWN)}")
            print("enable one for a stage with: ei skills enable NAME STAGE")
        if plugin.servers:
            print(
                "servers: installing a plugin never starts or contacts a server and never grants a "
                "tool. To lock one, review its command and run it yourself:"
            )
            for server in plugin.servers:
                print("  " + shlex.join(("ei", *server.tools_add_arguments())))

    def _listing(self, address: str, text: str) -> int:
        listing = self._marketplace.listing(address)
        found = listing.search(text)
        shown = self._safe(address, 200)
        for entry in found:
            description = self._safe(entry.description, self.SHOWN)
            print(
                f"{self._safe(entry.identifier(), 150)}  [{entry.kind} {self._safe(entry.target, 150)}]"
                + (f"  {description}" if description else "")
            )
            if entry.local:
                print(f"    ei plugins import {shlex.quote(entry.local)}")
        if not found:
            print(f"no plugin in {shown} matches {self._safe(text, 60)!r}")
        print(
            f"{len(found)} of {len(listing.entries)} plugins in the marketplace {self._safe(listing.name, 100)!r}; "
            "nothing is fetched or installed. Get a copy of a plugin yourself, read it, "
            "then: ei plugins import FOLDER"
        )
        if listing.unreadable:
            print(f"{listing.unreadable} entries could not be read and are not shown")
        return 0

    def _search(self, address: str, text: str) -> int:
        if address.lower().endswith(".json"):
            return self._listing(address, text)
        index = self._marketplace.index(address)
        found = index.search(text)
        shown = self._safe(address, 200)
        if not found:
            print(f"no plugin in {shown} matches {self._safe(text, 60)!r}")
            return 0
        for entry in found:
            description = self._safe(entry.description, self.SHOWN)
            print(
                f"{entry.identifier()}  {entry.sha256[:12]}"
                + (f"  {description}" if description else "")
            )
            print(f"    {self._safe(entry.url, 300)}")
        print(
            f"{len(found)} of {len(index.entries)} plugins in {shown}; nothing is installed. "
            "ei plugins fetch INDEX NAME saves one to read"
        )
        return 0

    def _fetch(self, arguments: argparse.Namespace) -> int:
        download = self._marketplace.download(arguments.index, arguments.name, arguments.output)
        entry = download.entry
        host = self._safe(urlsplit(entry.url).hostname or "the host", 100)
        print(
            f"fetched {entry.identifier()} from {host} (sha256 {entry.sha256[:12]} matches the index)"
        )
        print(f"saved to {download.path}")
        quoted = shlex.quote(str(download.path))
        print("nothing is installed. Read it, then install it:")
        print(f"  ei plugins show {quoted}")
        print(f"  ei plugins add {quoted}")
        return 0

    def _list(self, path: Path) -> int:
        lock = self._store.load(path)
        if lock is None:
            print(f"no plugin lock at {path}")
            return 0
        if not lock.entries:
            print(f"{path} locks no plugins")
            return 0
        for entry in sorted(lock.entries, key=lambda found: found.name):
            print(f"{entry.name}@{entry.version}  {entry.sha256[:12]}")
            skills = ", ".join(f"{name}" for name, _ in entry.skills) or "none"
            print(f"    skills installed: {skills}")
            print(f"    servers described: {', '.join(entry.servers) or 'none'}")
        return 0

    def _verify(self, path: Path, skill_path: Path) -> int:
        lock = self._store.load(path)
        if lock is None:
            print(f"error: no plugin lock at {path}", file=sys.stderr)
            return 2
        if not lock.entries:
            print(f"{path} locks no plugins; nothing to verify")
            return 0
        skills = self._skill_store.load(skill_path) or SkillLock()
        problems = self._verifier.problems(lock, skills, self._folder(path))
        for problem in problems:
            print(self._safe(problem, 400))
        if problems:
            print(f"{len(problems)} problems with {len(lock.entries)} installed plugins")
            return 1
        print(f"all {len(lock.entries)} plugins match the lock")
        return 0

    def _remove(self, arguments: argparse.Namespace, path: Path, skill_path: Path) -> int:
        lock = self._store.load(path)
        if lock is None:
            print(f"error: no plugin lock at {path}", file=sys.stderr)
            return 2
        skills = self._skill_store.load(skill_path) or SkillLock()
        removal = self._installer.remove(
            lock, skills, self._folder(path), self._skill_folder(skill_path), arguments.name
        )
        self._skill_store.save(skill_path, removal.skills)
        self._store.save(path, removal.lock)
        print(self._safe(f"removed plugin {arguments.name}", 300))
        if removal.removed:
            print("skills removed with it: " + ", ".join(removal.removed))
        if removal.kept:
            print(
                "skills left in place because they were locked again with other text: "
                + ", ".join(removal.kept)
            )
        print("servers it described stay in the tool lock if you locked them")
        print(f"wrote {skill_path} and {path}; review the change like any other commit")
        return 0

    @staticmethod
    def _safe(text: str, limit: int = 100) -> str:
        """Untrusted text on one line: anything not printable becomes a space, and long text is cut."""
        flat = " ".join("".join(c if c.isprintable() else " " for c in text).split())
        return flat if len(flat) <= limit else flat[: limit - 1] + "…"
