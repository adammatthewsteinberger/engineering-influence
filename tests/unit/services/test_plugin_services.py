# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""PluginInstaller and PluginLockVerifier: installing locks skills and records a hash, and does nothing else."""

import hashlib
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.plugins.toml_plugin_parser import TomlPluginParser
from engineering_influence.infrastructure.skills.toml_skill_parser import TomlSkillParser
from engineering_influence.infrastructure.skills.toml_skill_writer import TomlSkillWriter
from engineering_influence.interfaces.skill_files_interface import SkillFilesInterface
from engineering_influence.interfaces.skill_writer_interface import SkillWriterInterface
from engineering_influence.models.plugin_lock import PluginLock
from engineering_influence.models.plugin_lock_entry import PluginLockEntry
from engineering_influence.models.skill import Skill
from engineering_influence.models.skill_lock import SkillLock
from engineering_influence.models.skill_lock_entry import SkillLockEntry
from engineering_influence.services.interfaces.plugin_installer_interface import (
    PluginInstallerInterface,
)
from engineering_influence.services.interfaces.plugin_lock_verifier_interface import (
    PluginLockVerifierInterface,
)
from engineering_influence.services.plugin_installer import PluginInstaller
from engineering_influence.services.plugin_lock_verifier import PluginLockVerifier
from engineering_influence.services.skill_lock_editor import SkillLockEditor
from engineering_influence.services.skill_lock_verifier import SkillLockVerifier

PLUGINS, SKILLS = Path("/p/plugins"), Path("/p/skills")
SOURCE = Path("/elsewhere/research_pack.toml")
COPY = PLUGINS / "research_pack.toml"
HEAD = 'name = "research_pack"\nversion = 1\ndescription = "Sources and style."\n'
SERVERS = """
[[server]]
name = "docs"
url = "https://mcp.example.com/v1/mcp"
bearer_env = "DOCS_TOKEN"

[[server]]
name = "files"
command = ["/usr/local/bin/files-server"]
"""


def skill_text(name: str, version: int = 2) -> str:
    return (
        f'\n[[skill]]\nname = "{name}"\nversion = {version}\n\n[skill.parts]\n'
        'outline = "Prefer short chapters."\n'
    )


BUNDLE = (HEAD + SERVERS + skill_text("plain_style")).encode()
TWO_SKILLS = (HEAD + skill_text("alpha_one") + skill_text("beta_two")).encode()
SERVERS_ONLY = (HEAD + SERVERS).encode()


class Files(SkillFilesInterface):
    """Files in a dictionary that refuses to overwrite unless asked, like the real ones."""

    def __init__(self, files: dict[Path, bytes] | None = None) -> None:
        self.files = dict(files or {})
        self.broken: dict[Path, ApplicationError] = {}
        self.writes: list[Path] = []
        self.removed: list[Path] = []

    def read(self, path: Path) -> bytes | None:
        if path in self.broken:
            raise self.broken[path]
        return self.files.get(path)

    def write(self, path: Path, data: bytes, replace: bool) -> None:
        if path in self.files and not replace:
            raise ApplicationError(code="SKILL_FILE_EXISTS", message=f"{path} already exists")
        self.writes.append(path)
        self.files[path] = data

    def remove(self, path: Path) -> None:
        self.removed.append(path)
        self.files.pop(path, None)


class FailingWriter(SkillWriterInterface):
    def render(self, skill: Skill) -> bytes:
        if skill.name == "beta_two":
            raise ApplicationError(code="DISK_FULL", message="no space left")
        return TomlSkillWriter().render(skill)


def installer(files: Files, writer: SkillWriterInterface | None = None) -> PluginInstaller:
    skills = TomlSkillParser()
    editor = SkillLockEditor(files, skills, SkillLockVerifier(files, skills))
    return PluginInstaller(files, TomlPluginParser(skills), writer or TomlSkillWriter(), editor)


def verifier(files: Files) -> PluginLockVerifier:
    return PluginLockVerifier(files, TomlPluginParser(TomlSkillParser()))


def refused(action: object, code: str, status: int = 422) -> ApplicationError:
    with pytest.raises(ApplicationError) as error:
        action()  # type: ignore[operator]
    assert (error.value.code, error.value.http_status) == (code, status)
    return error.value


def installed(data: bytes = BUNDLE) -> tuple[Files, PluginLock, SkillLock]:
    files = Files({SOURCE: data})
    added = installer(files).add(PluginLock(), SkillLock(), PLUGINS, SKILLS, SOURCE)
    return files, added.lock, added.skills


def test_they_are_what_their_interfaces_say() -> None:
    assert isinstance(installer(Files()), PluginInstallerInterface)
    assert isinstance(verifier(Files()), PluginLockVerifierInterface)


# --------------------------------------------------------------------------------- inspect
def test_inspecting_reads_the_bundle_and_changes_nothing() -> None:
    files = Files({SOURCE: BUNDLE})
    bundle = installer(files).inspect(SOURCE)
    assert bundle.sha256 == hashlib.sha256(BUNDLE).hexdigest()
    assert bundle.plugin.identifier() == "research_pack@1"
    assert files.writes == [] and files.removed == []


def test_a_plugin_file_is_named_like_its_plugin() -> None:
    files = Files({Path("/x/Pack.toml"): BUNDLE, Path("/x/pack.txt"): BUNDLE})
    for name in ("/x/Pack.toml", "/x/pack.txt", "/x/pack"):
        error = refused(lambda name=name: installer(files).inspect(Path(name)), "PLUGIN_INVALID")  # type: ignore[misc]
        assert "named like research_pack.toml" in error.message


def test_a_missing_unreadable_or_invalid_file_is_refused() -> None:
    error = refused(lambda: installer(Files()).inspect(SOURCE), "PLUGIN_FILE_MISSING")
    assert str(SOURCE) in error.message
    files = Files()
    files.broken[SOURCE] = ApplicationError(code="SKILL_FILE_UNUSABLE", message="a link")
    refused(lambda: installer(files).inspect(SOURCE), "SKILL_FILE_UNUSABLE", 400)
    bad = Files({SOURCE: HEAD.encode() + b'grants = ["x"]\n'})
    assert (
        "unknown keys" in refused(lambda: installer(bad).inspect(SOURCE), "PLUGIN_INVALID").message
    )


# ------------------------------------------------------------------------------------- add
def test_adding_locks_the_skills_with_no_stage_keeps_the_bundle_and_records_its_hash() -> None:
    files, plugins, skills = installed()
    digest = hashlib.sha256(BUNDLE).hexdigest()
    entry = plugins.entry("research_pack")
    rendered = TomlSkillWriter().render(
        Skill("plain_style", 2, (("outline", "Prefer short chapters."),))
    )
    assert entry == PluginLockEntry(
        "research_pack",
        1,
        digest,
        ("docs", "files"),
        (("plain_style", hashlib.sha256(rendered).hexdigest()),),
    )
    assert files.files[COPY] == BUNDLE
    assert files.files[SKILLS / "plain_style.toml"] == rendered
    locked = skills.entry("plain_style")
    assert (
        locked is not None
        and locked.stages == ()
        and locked.sha256 == hashlib.sha256(rendered).hexdigest()
    )


def test_adding_grants_nothing_and_touches_no_server() -> None:
    files, _, skills = installed()
    assert all(entry.stages == () for entry in skills.entries)
    written = sorted(path.name for path in files.writes)
    assert written == ["plain_style.toml", "research_pack.toml"]
    assert not any("tool" in name for name in written)


def test_a_bundle_of_servers_alone_installs_a_record_and_no_skill() -> None:
    files = Files({SOURCE: SERVERS_ONLY})
    added = installer(files).add(PluginLock(), SkillLock(), PLUGINS, SKILLS, SOURCE)
    assert added.skills == SkillLock()
    assert files.writes == [COPY]
    entry = added.lock.entry("research_pack")
    assert entry is not None and entry.servers == ("docs", "files") and entry.skills == ()


def test_a_plugin_that_is_already_installed_is_refused_before_anything_is_written() -> None:
    files, plugins, skills = installed()
    before = dict(files.files)
    error = refused(
        lambda: installer(files).add(plugins, skills, PLUGINS, SKILLS, SOURCE),
        "PLUGIN_ALREADY_INSTALLED",
        409,
    )
    assert "ei plugins remove research_pack" in error.message
    assert files.files == before


def test_skills_that_are_already_locked_stop_the_install_before_anything_is_written() -> None:
    files = Files({SOURCE: TWO_SKILLS})
    taken = SkillLock((SkillLockEntry("beta_two", 1, "c" * 64),))
    error = refused(
        lambda: installer(files).add(PluginLock(), taken, PLUGINS, SKILLS, SOURCE),
        "PLUGIN_SKILL_CONFLICT",
        409,
    )
    assert "already locked: beta_two" in error.message and "ei skills remove NAME" in error.message
    assert files.writes == []


def test_a_stray_copy_of_the_bundle_stops_the_install_before_any_skill_is_written() -> None:
    files = Files({SOURCE: BUNDLE, COPY: b"old"})
    refused(
        lambda: installer(files).add(PluginLock(), SkillLock(), PLUGINS, SKILLS, SOURCE),
        "SKILL_FILE_EXISTS",
        400,
    )
    assert files.writes == [] and files.files[COPY] == b"old"


def test_a_failure_part_way_leaves_nothing_behind() -> None:
    files = Files({SOURCE: TWO_SKILLS})
    refused(
        lambda: installer(files, FailingWriter()).add(
            PluginLock(), SkillLock(), PLUGINS, SKILLS, SOURCE
        ),
        "DISK_FULL",
        400,
    )
    assert set(files.files) == {SOURCE}
    assert set(files.removed) == {COPY, SKILLS / "alpha_one.toml"}


# ---------------------------------------------------------------------------------- remove
def test_removing_takes_out_the_plugin_its_copy_and_the_skills_that_are_unchanged() -> None:
    files, plugins, skills = installed()
    removal = installer(files).remove(plugins, skills, PLUGINS, SKILLS, "research_pack")
    assert removal.lock == PluginLock() and removal.skills == SkillLock()
    assert (removal.removed, removal.kept) == (("plain_style",), ())
    assert COPY not in files.files and SKILLS / "plain_style.toml" not in files.files


def test_a_skill_locked_again_with_other_text_is_left_in_place_and_named() -> None:
    files, plugins, skills = installed()
    relocked = skills.with_entry(SkillLockEntry("plain_style", 9, "d" * 64, ("outline",)), True)
    removal = installer(files).remove(plugins, relocked, PLUGINS, SKILLS, "research_pack")
    assert (removal.removed, removal.kept) == ((), ("plain_style",))
    kept = removal.skills.entry("plain_style")
    assert kept is not None and kept.stages == ("outline",)
    assert SKILLS / "plain_style.toml" in files.files
    assert COPY not in files.files and removal.lock.entries == ()


def test_a_skill_that_is_already_gone_is_skipped() -> None:
    files, plugins, _ = installed()
    removal = installer(files).remove(plugins, SkillLock(), PLUGINS, SKILLS, "research_pack")
    assert (removal.removed, removal.kept) == ((), ())


def test_removing_a_plugin_that_is_not_installed_is_refused_and_deletes_nothing() -> None:
    files, plugins, skills = installed()
    refused(
        lambda: installer(files).remove(plugins, skills, PLUGINS, SKILLS, "none"), "PLUGIN_UNKNOWN"
    )
    assert files.removed == []


# --------------------------------------------------------------------------------- verifier
def test_an_installed_plugin_verifies() -> None:
    files, plugins, skills = installed()
    assert verifier(files).problems(plugins, skills, PLUGINS) == ()
    assert verifier(files).problems(PluginLock(), SkillLock(), PLUGINS) == ()


def test_a_missing_bundle_is_a_problem_that_names_the_path() -> None:
    files, plugins, skills = installed()
    del files.files[COPY]
    [problem] = verifier(files).problems(plugins, skills, PLUGINS)
    assert problem == f"plugin 'research_pack': {COPY} is missing"


def test_a_bundle_changed_by_one_character_is_a_problem() -> None:
    files, plugins, skills = installed()
    files.files[COPY] = BUNDLE.replace(b"Sources", b"sources")
    [problem] = verifier(files).problems(plugins, skills, PLUGINS)
    assert (
        problem == "plugin 'research_pack': research_pack.toml has changed since it was installed"
    )


def test_a_bundle_that_cannot_be_read_is_a_problem_with_the_reason() -> None:
    files, plugins, skills = installed()
    files.broken[COPY] = ApplicationError(code="SKILL_FILE_UNUSABLE", message="a link, so no")
    assert verifier(files).problems(plugins, skills, PLUGINS) == ("a link, so no",)


def test_a_bundle_whose_hash_matches_but_is_not_a_plugin_is_a_problem() -> None:
    junk = b"not = = toml"
    files = Files({COPY: junk})
    lock = PluginLock((PluginLockEntry("research_pack", 1, hashlib.sha256(junk).hexdigest()),))
    [problem] = verifier(files).problems(lock, SkillLock(), PLUGINS)
    assert problem.startswith("plugin 'research_pack': it is not valid TOML")


def test_a_version_that_disagrees_with_the_lock_is_a_problem() -> None:
    files, plugins, skills = installed()
    entry = plugins.entry("research_pack")
    assert entry is not None
    wrong = PluginLock(
        (PluginLockEntry("research_pack", 2, entry.sha256, entry.servers, entry.skills),)
    )
    [problem] = verifier(files).problems(wrong, skills, PLUGINS)
    assert problem == "plugin 'research_pack': its file is version 1, but the lock has 2"


def test_a_skill_that_is_no_longer_locked_or_was_locked_again_is_a_problem() -> None:
    files, plugins, _ = installed()
    [gone] = verifier(files).problems(plugins, SkillLock(), PLUGINS)
    assert gone == "plugin 'research_pack': its skill 'plain_style' is no longer locked"
    other = SkillLock((SkillLockEntry("plain_style", 2, "e" * 64),))
    [changed] = verifier(files).problems(plugins, other, PLUGINS)
    assert (
        changed
        == "plugin 'research_pack': its skill 'plain_style' was locked again with different text"
    )


def test_problems_come_in_name_order_across_plugins() -> None:
    files = Files()
    entries = tuple(PluginLockEntry(name, 1, "a" * 64) for name in ("zed_one", "alpha_one"))
    found = verifier(files).problems(PluginLock(entries), SkillLock(), PLUGINS)
    assert [line.split("'")[1] for line in found] == ["alpha_one", "zed_one"]
