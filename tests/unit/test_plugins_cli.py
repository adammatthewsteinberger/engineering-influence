# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""PluginsCli: look at, install, check and remove bundles, with everything a bundle says shown safely."""

import argparse
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interactions.cli.interfaces.plugins_cli_interface import (
    PluginsCliInterface,
)
from engineering_influence.interactions.cli.plugins_cli import PluginsCli
from engineering_influence.interfaces.plugin_lock_store_interface import PluginLockStoreInterface
from engineering_influence.interfaces.skill_lock_store_interface import SkillLockStoreInterface
from engineering_influence.models.plugin import Plugin
from engineering_influence.models.plugin_addition import PluginAddition
from engineering_influence.models.plugin_bundle import PluginBundle
from engineering_influence.models.plugin_conversion import PluginConversion
from engineering_influence.models.plugin_download import PluginDownload
from engineering_influence.models.plugin_import_result import PluginImportResult
from engineering_influence.models.plugin_index import PluginIndex
from engineering_influence.models.plugin_index_entry import PluginIndexEntry
from engineering_influence.models.plugin_lock import PluginLock
from engineering_influence.models.plugin_lock_entry import PluginLockEntry
from engineering_influence.models.plugin_removal import PluginRemoval
from engineering_influence.models.plugin_server import PluginServer
from engineering_influence.models.skill import Skill
from engineering_influence.models.skill_lock import SkillLock
from engineering_influence.models.skill_lock_entry import SkillLockEntry
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

A, B = "a" * 64, "b" * 64


def plugin(**changes: object) -> Plugin:
    fields: dict[str, object] = {
        "name": "research_pack",
        "version": 1,
        "description": "Sources and style.",
        "servers": (
            PluginServer("docs", url="https://mcp.example.com/mcp", bearer_env="DOCS_TOKEN"),
            PluginServer("files", command=("/opt/files server", "/opt/a.js"), env=("ROOT",)),
        ),
        "skills": (Skill("plain_style", 2, (("outline", "Prefer short chapters."),)),),
    }
    return Plugin(**{**fields, **changes})  # type: ignore[arg-type]


def entry(name: str = "research_pack") -> PluginLockEntry:
    return PluginLockEntry(name, 1, A, ("docs", "files"), (("plain_style", B),))


class Installer(PluginInstallerInterface):
    def __init__(self, fail: Exception | None = None, made: Plugin | None = None) -> None:
        self.fail, self.made = fail, made or plugin()
        self.calls: list[tuple[object, ...]] = []

    def _go(self, *call: object) -> None:
        self.calls.append(call)
        if self.fail:
            raise self.fail

    def inspect(self, source: Path) -> PluginBundle:
        self._go("inspect", source)
        return PluginBundle(self.made, A)

    def add(
        self,
        plugins: PluginLock,
        skills: SkillLock,
        plugin_folder: Path,
        skill_folder: Path,
        source: Path,
    ) -> PluginAddition:
        self._go("add", plugin_folder, skill_folder, source)
        grown = skills.with_entry(SkillLockEntry("plain_style", 2, B), True)
        return PluginAddition(plugins.with_entry(entry()), grown, PluginBundle(self.made, A))

    def remove(
        self,
        plugins: PluginLock,
        skills: SkillLock,
        plugin_folder: Path,
        skill_folder: Path,
        name: str,
    ) -> PluginRemoval:
        self._go("remove", plugin_folder, skill_folder, name)
        return PluginRemoval(plugins.without(name), SkillLock(), self.removed, self.kept)

    removed: tuple[str, ...] = ("plain_style",)
    kept: tuple[str, ...] = ()


LISTED = PluginIndexEntry(
    "research_pack",
    1,
    "https://plugins.example.com/v1/research_pack.toml",
    A,
    "Sources and style.",
)


class Marketplace(PluginMarketplaceInterface):
    def __init__(self, *entries: PluginIndexEntry, fail: Exception | None = None) -> None:
        self.entries, self.fail = entries, fail
        self.calls: list[tuple[object, ...]] = []

    def index(self, address: str) -> PluginIndex:
        self.calls.append(("index", address))
        if self.fail:
            raise self.fail
        return PluginIndex(tuple(sorted(self.entries, key=lambda entry: entry.name)))

    def download(self, address: str, name: str, folder: Path) -> PluginDownload:
        self.calls.append(("download", address, name, folder))
        if self.fail:
            raise self.fail
        entry = next(found for found in self.entries if found.name == name)
        return PluginDownload(entry, PluginBundle(plugin(), A), folder / f"{name}.toml")


class Importer(PluginImporterInterface):
    def __init__(
        self,
        fail: Exception | None = None,
        conversion: PluginConversion | None = None,
    ) -> None:
        self.fail = fail
        self.conversion = conversion or PluginConversion(plugin())
        self.calls: list[tuple[object, ...]] = []

    def import_plugin(
        self, source: Path, name: str | None, version: int, target: Path | None
    ) -> PluginImportResult:
        self.calls.append((source, name, version, target))
        if self.fail:
            raise self.fail
        return PluginImportResult(self.conversion, str(target or "research_pack.toml"))


class Verifier(PluginLockVerifierInterface):
    def __init__(self, *problems: str) -> None:
        self.found = problems
        self.asked: list[tuple[PluginLock, SkillLock, Path]] = []

    def problems(self, plugins: PluginLock, skills: SkillLock, folder: Path) -> tuple[str, ...]:
        self.asked.append((plugins, skills, folder))
        return self.found


class Store(PluginLockStoreInterface):
    def __init__(self, lock: PluginLock | None = None, fail: Exception | None = None) -> None:
        self.lock, self.fail = lock, fail
        self.loaded: list[Path] = []
        self.saved: list[tuple[Path, PluginLock]] = []
        self.order: list[str] = []

    def load(self, path: Path) -> PluginLock | None:
        self.loaded.append(path)
        if self.fail:
            raise self.fail
        return self.lock

    def save(self, path: Path, lock: PluginLock) -> None:
        self.order.append("plugins")
        self.saved.append((path, lock))


class SkillStore(SkillLockStoreInterface):
    def __init__(self, lock: SkillLock | None = None, order: list[str] | None = None) -> None:
        self.lock = lock
        self.loaded: list[Path] = []
        self.saved: list[tuple[Path, SkillLock]] = []
        self.order = order if order is not None else []

    def load(self, path: Path) -> SkillLock | None:
        self.loaded.append(path)
        return self.lock

    def save(self, path: Path, lock: SkillLock) -> None:
        self.order.append("skills")
        self.saved.append((path, lock))


def cli(
    store: Store | None = None,
    skills: SkillStore | None = None,
    installer: Installer | None = None,
    importer: Importer | None = None,
    verifier: Verifier | None = None,
    environment: dict[str, str] | None = None,
    market: Marketplace | None = None,
) -> tuple[PluginsCli, Store, SkillStore, Installer, Verifier]:
    made = (
        store or Store(),
        skills or SkillStore(),
        installer or Installer(),
        verifier or Verifier(),
    )
    made[1].order = made[0].order
    return PluginsCli(
        made[2],
        importer or Importer(),
        made[3],
        market or Marketplace(),
        made[0],
        made[1],
        environment or {},
    ), *made


def run(plugins: PluginsCli, *argv: str) -> int:
    parser = argparse.ArgumentParser()
    plugins.register(parser.add_subparsers(dest="command"))
    return plugins.run(parser.parse_args(["plugins", *argv]))


def test_it_is_a_plugins_cli() -> None:
    assert isinstance(cli()[0], PluginsCliInterface)


# ------------------------------------------------------------------------------------ show
def test_show_describes_what_installing_would_do_and_changes_nothing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    plugins, store, skills, installer, _ = cli()
    assert run(plugins, "show", "/x/research_pack.toml") == 0
    out = capsys.readouterr().out
    assert installer.calls == [("inspect", Path("/x/research_pack.toml"))]
    assert store.saved == [] and skills.saved == [] and store.loaded == []
    assert f"research_pack@1 (bundle sha256 {A[:12]}): 2 servers, 1 skills" in out
    assert "  Sources and style." in out
    assert "  plain_style@2, text for outline" in out
    assert "    outline (22 characters): Prefer short chapters." in out
    assert "enable one for a stage with: ei skills enable NAME STAGE" in out
    assert "installing a plugin never starts or contacts a server and never grants a tool" in out
    assert "  ei tools add --bearer-env DOCS_TOKEN --url https://mcp.example.com/mcp docs" in out
    assert "  ei tools add --env ROOT files -- '/opt/files server' /opt/a.js" in out


def test_show_of_a_bundle_with_only_servers_or_only_skills_leaves_the_other_part_out(
    capsys: pytest.CaptureFixture[str],
) -> None:
    only_servers = Installer(made=plugin(skills=(), description=""))
    assert run(cli(installer=only_servers)[0], "show", "/x/research_pack.toml") == 0
    out = capsys.readouterr().out
    assert "skills: text that will be added" not in out and "ei skills enable" not in out
    assert "ei tools add" in out and "Sources and style." not in out
    assert not any(line and not line.strip() for line in out.splitlines())
    only_skills = Installer(made=plugin(servers=()))
    assert run(cli(installer=only_skills)[0], "show", "/x/research_pack.toml") == 0
    out = capsys.readouterr().out
    assert "servers: installing" not in out and "ei skills enable" in out


# ------------------------------------------------------------------------------------- add
def test_add_installs_saves_the_skill_lock_then_the_plugin_lock_and_says_what_it_did(
    capsys: pytest.CaptureFixture[str],
) -> None:
    plugins, store, skills, installer, _ = cli()
    status = run(
        plugins, "add", "--lock", "/x/p/l.toml", "--skill-lock", "/x/s/k.toml", "/tmp/r.toml"
    )
    assert status == 0
    assert installer.calls == [
        ("add", Path("/x/p/plugins"), Path("/x/s/skills"), Path("/tmp/r.toml"))
    ]
    assert store.saved[0][0] == Path("/x/p/l.toml") and skills.saved[0][0] == Path("/x/s/k.toml")
    assert store.order == ["skills", "plugins"]
    out = capsys.readouterr().out
    assert f"installed research_pack@1 (bundle sha256 {A[:12]})" in out
    assert "wrote /x/s/k.toml and /x/p/l.toml; review the change like any other commit" in out


def test_add_extends_the_locks_that_are_there() -> None:
    plugins, store, skills, _, _ = cli(
        Store(PluginLock((entry("other_one"),))),
        SkillStore(SkillLock((SkillLockEntry("existing_one", 1, A),))),
    )
    assert run(plugins, "add", "--lock", "/p/l.toml", "--skill-lock", "/p/k.toml", "x.toml") == 0
    assert store.saved[0][1].names() == ("other_one", "research_pack")
    assert skills.saved[0][1].names() == ("existing_one", "plain_style")


def test_the_locks_are_the_flag_then_the_environment_then_the_default() -> None:
    plugins, store, skills, _, _ = cli(
        environment={"EI_PLUGIN_LOCK": "/env/p.toml", "EI_SKILL_LOCK": "/env/s.toml"}
    )
    run(plugins, "add", "x.toml")
    assert store.loaded == [Path("/env/p.toml")] and skills.loaded == [Path("/env/s.toml")]
    run(plugins, "add", "--lock", "/f/p.toml", "--skill-lock", "/f/s.toml", "x.toml")
    assert store.loaded[-1] == Path("/f/p.toml") and skills.loaded[-1] == Path("/f/s.toml")
    default, default_store, default_skills, _, _ = cli()
    run(default, "add", "x.toml")
    assert default_store.loaded == [Path("ei-plugins.lock.toml")]
    assert default_skills.loaded == [Path("ei-skills.lock.toml")]
    blank, blank_store, blank_skills, _, _ = cli(
        environment={"EI_PLUGIN_LOCK": " ", "EI_SKILL_LOCK": " "}
    )
    run(blank, "add", "x.toml")
    assert blank_store.loaded == [Path("ei-plugins.lock.toml")]
    assert blank_skills.loaded == [Path("ei-skills.lock.toml")]


def test_the_bundles_and_skills_live_in_folders_beside_their_locks() -> None:
    plugins, _, _, installer, _ = cli()
    run(plugins, "add", "x.toml")
    assert installer.calls[0][1:3] == (Path("plugins"), Path("skills"))


def test_an_install_the_installer_refuses_is_a_setup_error_and_nothing_is_saved(
    capsys: pytest.CaptureFixture[str],
) -> None:
    refusal = ApplicationError(
        code="PLUGIN_INVALID", message="it has unknown keys", http_status=422
    )
    plugins, store, skills, _, _ = cli(installer=Installer(fail=refusal))
    assert run(plugins, "add", "--lock", "/p/l.toml", "x.toml") == 2
    assert "error: it has unknown keys" in capsys.readouterr().err
    assert store.saved == [] and skills.saved == []


def test_a_value_error_and_an_os_error_are_setup_errors_too(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run(cli(installer=Installer(fail=ValueError("not good")))[0], "show", "x.toml") == 2
    assert "error: not good" in capsys.readouterr().err
    assert run(cli(store=Store(fail=OSError(28, "No space left on device")))[0], "list") == 2
    assert "error: No space left on device" in capsys.readouterr().err
    assert run(cli(store=Store(fail=OSError()))[0], "list") == 2
    assert "error: OSError" in capsys.readouterr().err


# ------------------------------------------------------------------------------------ list
def test_list_with_no_lock_or_an_empty_one_says_so(capsys: pytest.CaptureFixture[str]) -> None:
    assert run(cli()[0], "list", "--lock", "/p/none.toml") == 0
    assert capsys.readouterr().out == "no plugin lock at /p/none.toml\n"
    assert run(cli(Store(PluginLock()))[0], "list", "--lock", "/p/l.toml") == 0
    assert capsys.readouterr().out == "/p/l.toml locks no plugins\n"


def test_list_shows_each_plugin_with_its_short_hash_skills_and_servers_in_name_order(
    capsys: pytest.CaptureFixture[str],
) -> None:
    bare = PluginLockEntry("alpha_one", 4, B)
    assert (
        run(cli(Store(PluginLock((entry("zed_one"), bare))))[0], "list", "--lock", "/p/l.toml") == 0
    )
    assert capsys.readouterr().out == (
        f"alpha_one@4  {B[:12]}\n    skills installed: none\n    servers described: none\n"
        f"zed_one@1  {A[:12]}\n    skills installed: plain_style\n    servers described: docs, files\n"
    )


# ---------------------------------------------------------------------------------- verify
def test_verify_when_everything_matches_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    lock = PluginLock((entry("a_one"), entry("b_one")))
    plugins, _, _, _, verifier = cli(Store(lock), SkillStore(SkillLock()))
    assert run(plugins, "verify", "--lock", "/p/l.toml", "--skill-lock", "/q/k.toml") == 0
    assert capsys.readouterr().out == "all 2 plugins match the lock\n"
    assert verifier.asked == [(lock, SkillLock(), Path("/p/plugins"))]


def test_verify_lists_each_problem_and_exits_one(capsys: pytest.CaptureFixture[str]) -> None:
    lock = PluginLock((entry("a_one"), entry("b_one")))
    found = Verifier("plugin 'a_one': changed", "plugin 'b_one': gone")
    assert run(cli(Store(lock), verifier=found)[0], "verify", "--lock", "/p/l.toml") == 1
    assert capsys.readouterr().out == (
        "plugin 'a_one': changed\nplugin 'b_one': gone\n2 problems with 2 installed plugins\n"
    )


def test_verify_with_no_lock_is_a_setup_error_and_an_empty_lock_has_nothing_to_do(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert run(cli()[0], "verify", "--lock", "/p/none.toml") == 2
    assert "error: no plugin lock at /p/none.toml" in capsys.readouterr().err
    plugins, _, _, _, verifier = cli(Store(PluginLock()))
    assert run(plugins, "verify", "--lock", "/p/l.toml") == 0
    assert capsys.readouterr().out == "/p/l.toml locks no plugins; nothing to verify\n"
    assert verifier.asked == []


# ---------------------------------------------------------------------------------- remove
def test_remove_undoes_the_install_and_says_what_stayed(capsys: pytest.CaptureFixture[str]) -> None:
    installer = Installer()
    installer.kept = ("other_skill",)
    plugins, store, _, _, _ = cli(Store(PluginLock((entry(),))), SkillStore(SkillLock()), installer)
    assert (
        run(plugins, "remove", "--lock", "/p/l.toml", "--skill-lock", "/q/k.toml", "research_pack")
        == 0
    )
    assert installer.calls == [("remove", Path("/p/plugins"), Path("/q/skills"), "research_pack")]
    assert store.order == ["skills", "plugins"] and store.saved[0][1].entries == ()
    out = capsys.readouterr().out
    assert "removed plugin research_pack" in out
    assert "skills removed with it: plain_style" in out
    assert "skills left in place because they were locked again with other text: other_skill" in out
    assert "servers it described stay in the tool lock if you locked them" in out
    assert "wrote /q/k.toml and /p/l.toml; review the change like any other commit" in out


def test_remove_says_nothing_about_skills_when_there_were_none(
    capsys: pytest.CaptureFixture[str],
) -> None:
    installer = Installer()
    installer.removed = ()
    plugins = cli(Store(PluginLock((entry(),))), installer=installer)[0]
    assert run(plugins, "remove", "--lock", "/p/l.toml", "research_pack") == 0
    out = capsys.readouterr().out
    assert "skills removed with it" not in out and "left in place" not in out


def test_remove_with_no_lock_is_a_setup_error(capsys: pytest.CaptureFixture[str]) -> None:
    plugins, _, _, installer, _ = cli()
    assert run(plugins, "remove", "--lock", "/p/none.toml", "x") == 2
    assert "error: no plugin lock at /p/none.toml" in capsys.readouterr().err
    assert installer.calls == []


# ------------------------------------------------------------ what a bundle says is data
def test_what_a_bundle_says_is_printed_on_one_line_cleaned_and_cut(
    capsys: pytest.CaptureFixture[str],
) -> None:
    text = "Line one.\nLine two.\t" + "x" * 300
    made = plugin(
        skills=(Skill("plain_style", 2, (("outline", text),)),),
        description="Fine    red " + "y" * 200,
    )
    assert run(cli(installer=Installer(made=made))[0], "show", "x.toml") == 0
    out = capsys.readouterr().out
    [description] = [line for line in out.splitlines() if line.startswith("  Fine red")]
    assert len(description) == 102 and description.endswith("…")
    [part] = [line for line in out.splitlines() if line.startswith("    outline (")]
    assert part.startswith("    outline (320 characters): Line one. Line two. xxx")
    assert part.endswith("…") and len(part.split(": ", 1)[1]) == 100


def test_a_problem_text_from_a_file_is_cleaned_and_cut_too(
    capsys: pytest.CaptureFixture[str],
) -> None:
    nasty = "plugin 'a_one': line\x1b[31mred\nnext " + "y" * 600
    lock = PluginLock((entry("a_one"),))
    assert run(cli(Store(lock), verifier=Verifier(nasty))[0], "verify", "--lock", "/p/l.toml") == 1
    first = capsys.readouterr().out.splitlines()[0]
    assert "\x1b" not in first and first.startswith("plugin 'a_one': line [31mred next")
    assert len(first) == 400 and first.endswith("…")


# --------------------------------------------------------------------------- search and fetch
def second(name: str = "beta_two", description: str = "House STYLE.") -> PluginIndexEntry:
    return PluginIndexEntry(name, 3, f"https://other.example.com/{name}.toml", B, description)


def test_search_lists_each_plugin_with_its_hash_and_address_and_installs_nothing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    market = Marketplace(second(), LISTED)
    plugins, store, skills, installer, _ = cli(market=market)
    assert run(plugins, "search", "https://market.example.com/index.toml") == 0
    out = capsys.readouterr().out
    assert market.calls == [("index", "https://market.example.com/index.toml")]
    assert out.index("beta_two@3") < out.index("research_pack@1")
    assert f"research_pack@1  {A[:12]}  Sources and style.\n" in out
    assert "    https://plugins.example.com/v1/research_pack.toml\n" in out
    assert "2 of 2 plugins in https://market.example.com/index.toml; nothing is installed." in out
    assert "ei plugins fetch INDEX NAME saves one to read" in out
    assert store.saved == [] and skills.saved == [] and installer.calls == []


def test_search_with_text_narrows_the_list_and_says_how_many_of_how_many(
    capsys: pytest.CaptureFixture[str],
) -> None:
    plugins = cli(market=Marketplace(second(), LISTED))[0]
    assert run(plugins, "search", "/market/index.toml", "style") == 0
    out = capsys.readouterr().out
    assert "beta_two@3" in out and "research_pack@1" in out
    assert "2 of 2 plugins" in out
    assert run(plugins, "search", "/market/index.toml", "house") == 0
    out = capsys.readouterr().out
    assert "beta_two@3" in out and "research_pack" not in out and "1 of 2 plugins" in out


def test_search_with_no_match_says_so_and_is_not_an_error(
    capsys: pytest.CaptureFixture[str],
) -> None:
    plugins = cli(market=Marketplace(LISTED))[0]
    assert run(plugins, "search", "/market/index.toml", "zebra") == 0
    assert capsys.readouterr().out == "no plugin in /market/index.toml matches 'zebra'\n"


def test_an_entry_with_no_description_is_listed_without_a_trailing_gap(
    capsys: pytest.CaptureFixture[str],
) -> None:
    plugins = cli(market=Marketplace(second(description="")))[0]
    assert run(plugins, "search", "/market/index.toml") == 0
    first = capsys.readouterr().out.splitlines()[0]
    assert first == f"beta_two@3  {B[:12]}"


def test_what_an_index_says_is_printed_cleaned_and_cut(capsys: pytest.CaptureFixture[str]) -> None:
    long = PluginIndexEntry("long_one", 1, "https://x.example.com/" + "p" * 400, A, "y" * 200)
    plugins = cli(market=Marketplace(long))[0]
    assert run(plugins, "search", "/market/index.toml") == 0
    lines = capsys.readouterr().out.splitlines()
    description = lines[0].split("  ", 2)[2]
    assert len(description) == 100 and description.endswith("…")
    assert len(lines[1].strip()) == 300 and lines[1].endswith("…")


def test_fetch_downloads_checks_and_says_what_to_do_next_without_installing(
    capsys: pytest.CaptureFixture[str],
) -> None:
    market = Marketplace(LISTED)
    plugins, store, skills, installer, _ = cli(market=market)
    assert run(plugins, "fetch", "https://market.example.com/i.toml", "research_pack") == 0
    out = capsys.readouterr().out
    assert market.calls[-1] == (
        "download",
        "https://market.example.com/i.toml",
        "research_pack",
        Path("."),
    )
    assert (
        f"fetched research_pack@1 from plugins.example.com (sha256 {A[:12]} matches the index)"
        in out
    )
    assert "saved to research_pack.toml" in out
    assert "nothing is installed. Read it, then install it:" in out
    assert "  ei plugins show research_pack.toml\n  ei plugins add research_pack.toml\n" in out
    assert store.saved == [] and skills.saved == [] and installer.calls == []


def test_fetch_saves_where_asked_and_quotes_a_path_with_a_space(
    capsys: pytest.CaptureFixture[str],
) -> None:
    market = Marketplace(LISTED)
    plugins = cli(market=market)[0]
    assert (
        run(
            plugins, "fetch", "/market/index.toml", "research_pack", "--output", "/tmp/my downloads"
        )
        == 0
    )
    out = capsys.readouterr().out
    assert market.calls[-1][3] == Path("/tmp/my downloads")
    assert "saved to /tmp/my downloads/research_pack.toml" in out
    assert "ei plugins show '/tmp/my downloads/research_pack.toml'" in out


def test_a_marketplace_error_is_a_setup_error_for_both_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    refusal = ApplicationError(
        code="PLUGIN_HASH_MISMATCH", message="not what the index promised", http_status=422
    )
    market = Marketplace(LISTED, fail=refusal)
    plugins = cli(market=market)[0]
    assert run(plugins, "search", "/market/index.toml") == 2
    assert "error: not what the index promised" in capsys.readouterr().err
    assert run(plugins, "fetch", "/market/index.toml", "research_pack") == 2
    assert "error: not what the index promised" in capsys.readouterr().err


# ---------------------------------------------------------------------------------- import
def test_import_passes_everything_on_and_says_what_it_wrote_and_what_to_do_next(
    capsys: pytest.CaptureFixture[str],
) -> None:
    importer = Importer()
    plugins, store, skills, _, _ = cli(importer=importer)
    code = run(
        plugins,
        "import",
        "downloads/research-pack",
        "--name",
        "mine",
        "--version",
        "3",
        "--out",
        "out/mine.toml",
    )
    assert code == 0
    assert importer.calls == [(Path("downloads/research-pack"), "mine", 3, Path("out/mine.toml"))]
    assert store.saved == [] and skills.saved == [] and store.loaded == []
    out = capsys.readouterr().out
    assert "wrote out/mine.toml: research_pack@1" in out
    assert "  skill plain_style: 0 reference sections, 0 characters" in out
    assert "  server docs: address" in out and "  server files: command" in out
    assert "read the file before you install it" in out
    assert "then: ei plugins show out/mine.toml" in out
    assert "skipped" not in out and "note:" not in out and "set aside" not in out


def test_import_defaults_are_no_name_version_one_and_the_default_file() -> None:
    importer = Importer()
    assert run(cli(importer=importer)[0], "import", "folder") == 0
    assert importer.calls == [(Path("folder"), None, 1, None)]


def test_import_says_what_it_skipped_noted_and_set_aside_and_shows_it_safely(
    capsys: pytest.CaptureFixture[str],
) -> None:
    conversion = PluginConversion(
        plugin(),
        (("server a\x1b[31m", "no \x07launcher"),),
        ("server b: env not copied",),
        ("hooks: nothing runs",),
    )
    assert run(cli(importer=Importer(conversion=conversion))[0], "import", "folder") == 0
    out = capsys.readouterr().out
    assert "  skipped server a [31m: no launcher" in out
    assert "  note: server b: env not copied" in out
    assert "  set aside: hooks: nothing runs" in out
    assert "\x1b" not in out and "\x07" not in out


def test_import_that_cannot_be_done_exits_2_with_one_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    failure = ApplicationError(
        "PLUGIN_IMPORT_EMPTY", "nothing in the folder could be imported", 422
    )
    assert run(cli(importer=Importer(failure))[0], "import", "folder") == 2
    assert capsys.readouterr().err.strip() == "error: nothing in the folder could be imported"
