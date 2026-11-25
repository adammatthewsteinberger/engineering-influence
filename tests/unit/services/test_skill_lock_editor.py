# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""SkillLockEditor: every change is one a person asked for, and none of them runs anything."""

import hashlib
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.skills.toml_skill_parser import TomlSkillParser
from engineering_influence.interfaces.skill_files_interface import SkillFilesInterface
from engineering_influence.models.skill_lock import SkillLock
from engineering_influence.models.skill_lock_entry import SkillLockEntry
from engineering_influence.services.interfaces.skill_lock_editor_interface import (
    SkillLockEditorInterface,
)
from engineering_influence.services.skill_lock_editor import SkillLockEditor
from engineering_influence.services.skill_lock_verifier import SkillLockVerifier

FOLDER = Path("/project/skills")
SOURCE = Path("/elsewhere/plain_style.toml")
COPY = FOLDER / "plain_style.toml"


class MemoryFiles(SkillFilesInterface):
    """Skill files held in a dictionary, remembering what was asked of them."""

    def __init__(self, files: dict[Path, bytes] | None = None) -> None:
        self.files = dict(files or {})
        self.broken: dict[Path, ApplicationError] = {}
        self.reads: list[Path] = []

    def read(self, path: Path) -> bytes | None:
        self.reads.append(path)
        if path in self.broken:
            raise self.broken[path]
        return self.files.get(path)

    def write(self, path: Path, data: bytes, replace: bool) -> None:
        self.files[path] = data

    def remove(self, path: Path) -> None:
        self.files.pop(path, None)


def text(name: str = "plain_style", version: int = 2, **parts: str) -> bytes:
    given = parts or {"outline": "Prefer short sentences.", "research": "Say where you read it."}
    body = "".join(f'{stage} = "{words}"\n' for stage, words in given.items())
    return f'name = "{name}"\nversion = {version}\n[parts]\n{body}'.encode()


def locked(
    data: bytes, name: str = "plain_style", version: int = 2, stages: tuple[str, ...] = ()
) -> SkillLockEntry:
    return SkillLockEntry(name, version, hashlib.sha256(data).hexdigest(), stages)


class RecordingFiles(MemoryFiles):
    def __init__(self, files: dict[Path, bytes] | None = None) -> None:
        super().__init__(files)
        self.writes: list[tuple[Path, bytes, bool]] = []
        self.removed: list[Path] = []

    def write(self, path: Path, data: bytes, replace: bool) -> None:
        self.writes.append((path, data, replace))
        super().write(path, data, replace)

    def remove(self, path: Path) -> None:
        self.removed.append(path)
        super().remove(path)


def editor(files: RecordingFiles) -> SkillLockEditor:
    parser = TomlSkillParser()
    return SkillLockEditor(files, parser, SkillLockVerifier(files, parser))


def refused(action: object, code: str, status: int = 422) -> ApplicationError:
    with pytest.raises(ApplicationError) as error:
        action()  # type: ignore[operator]
    assert (error.value.code, error.value.http_status) == (code, status)
    return error.value


def test_it_is_a_skill_lock_editor() -> None:
    assert isinstance(editor(RecordingFiles()), SkillLockEditorInterface)


# ------------------------------------------------------------------------------------- add
def test_adding_locks_the_hash_of_the_bytes_read_keeps_a_copy_and_enables_nothing() -> None:
    data = text()
    files = RecordingFiles({SOURCE: data})
    added = editor(files).add(SkillLock(), FOLDER, SOURCE, replace=False)
    found = added.lock.entry("plain_style")
    assert found == SkillLockEntry("plain_style", 2, hashlib.sha256(data).hexdigest(), ())
    assert added.skill.identifier() == "plain_style@2"
    assert files.writes == [(COPY, data, False)]


def test_a_skill_file_is_named_like_its_skill() -> None:
    files = RecordingFiles({Path("/x/Plain.toml"): text(), Path("/x/plain.txt"): text()})
    for name in ("/x/Plain.toml", "/x/plain.txt", "/x/plain_style"):
        error = refused(
            lambda name=name: editor(files).add(SkillLock(), FOLDER, Path(name), False),  # type: ignore[misc]
            "SKILL_INVALID",
        )
        assert "named like plain_style.toml" in error.message
    assert files.writes == [] and files.reads == []


def test_a_skill_that_is_already_locked_is_not_locked_again_unless_asked() -> None:
    files = RecordingFiles({SOURCE: text()})
    lock = SkillLock((locked(text(), stages=("outline",)),))
    error = refused(
        lambda: editor(files).add(lock, FOLDER, SOURCE, replace=False), "SKILL_ALREADY_LOCKED", 409
    )
    assert "use --replace" in error.message
    assert files.reads == [] and files.writes == []


def test_locking_again_with_replace_clears_the_stages_because_the_new_text_is_unapproved() -> None:
    new = text(version=3)
    files = RecordingFiles({SOURCE: new})
    lock = SkillLock((locked(text(), stages=("outline", "research")),))
    added = editor(files).add(lock, FOLDER, SOURCE, replace=True)
    found = added.lock.entry("plain_style")
    assert found is not None and found.stages == () and found.version == 3
    assert found.sha256 == hashlib.sha256(new).hexdigest()
    assert files.writes == [(COPY, new, True)]


def test_a_missing_source_is_refused() -> None:
    files = RecordingFiles()
    error = refused(
        lambda: editor(files).add(SkillLock(), FOLDER, SOURCE, False), "SKILL_FILE_MISSING"
    )
    assert str(SOURCE) in error.message


def test_a_source_that_is_not_a_skill_is_refused_and_nothing_is_kept() -> None:
    files = RecordingFiles({SOURCE: b'name = "plain_style"\nversion = 1\ncommand = "rm"\n'})
    error = refused(lambda: editor(files).add(SkillLock(), FOLDER, SOURCE, False), "SKILL_INVALID")
    assert "unknown keys" in error.message and files.writes == []


def test_a_skill_already_in_the_folder_is_locked_without_copying_it_onto_itself() -> None:
    data = text()
    files = RecordingFiles({COPY: data})
    added = editor(files).add(SkillLock(), FOLDER, COPY, replace=False)
    assert added.lock.names() == ("plain_style",) and files.writes == []


def test_an_unreadable_source_stops_the_add() -> None:
    files = RecordingFiles()
    files.broken[SOURCE] = ApplicationError(code="SKILL_FILE_UNUSABLE", message="a link")
    refused(
        lambda: editor(files).add(SkillLock(), FOLDER, SOURCE, False), "SKILL_FILE_UNUSABLE", 400
    )
    assert files.writes == []


# ---------------------------------------------------------------------------------- enable
def lock_with(data: bytes, *stages: str) -> SkillLock:
    return SkillLock((locked(data, stages=stages),))


def test_enabling_a_stage_the_skill_has_text_for_adds_it_in_order() -> None:
    data = text()
    files = RecordingFiles({COPY: data})
    first = editor(files).enable(lock_with(data), FOLDER, "plain_style", "research")
    second = editor(files).enable(first, FOLDER, "plain_style", "outline")
    found = second.entry("plain_style")
    assert found is not None and found.stages == ("outline", "research")


def test_enabling_a_skill_that_is_not_locked_is_refused() -> None:
    error = refused(
        lambda: editor(RecordingFiles()).enable(SkillLock(), FOLDER, "plain_style", "outline"),
        "SKILL_UNKNOWN",
    )
    assert "no skill named 'plain_style' is locked" in error.message


def test_enabling_checks_the_skill_against_its_hash_first() -> None:
    files = RecordingFiles({COPY: text(outline="Changed.", research="Changed.")})
    refused(
        lambda: editor(files).enable(lock_with(text()), FOLDER, "plain_style", "outline"),
        "SKILL_LOCK_MISMATCH",
        503,
    )


def test_a_stage_the_skill_says_nothing_about_is_refused_and_the_text_it_has_is_listed() -> None:
    data = text()
    files = RecordingFiles({COPY: data})
    error = refused(
        lambda: editor(files).enable(lock_with(data), FOLDER, "plain_style", "brief"),
        "SKILL_STAGE_UNKNOWN",
    )
    assert "has no text for stage 'brief'" in error.message
    assert "it has text for: outline, research" in error.message


def test_a_stage_may_not_carry_more_than_four_skills() -> None:
    entries = []
    files = RecordingFiles()
    for number in range(5):
        name = f"skill_{number}"
        data = text(name)
        files.files[FOLDER / f"{name}.toml"] = data
        entries.append(locked(data, name, stages=("outline",) if number < 4 else ()))
    error = refused(
        lambda: editor(files).enable(SkillLock(tuple(entries)), FOLDER, "skill_4", "outline"),
        "SKILL_LOCK_INVALID",
    )
    assert "the most is 4" in error.message


# --------------------------------------------------------------------------------- disable
def test_disabling_takes_one_stage_away_and_keeps_the_others() -> None:
    lock = lock_with(text(), "outline", "research")
    found = editor(RecordingFiles()).disable(lock, "plain_style", "outline").entry("plain_style")
    assert found is not None and found.stages == ("research",)


def test_disabling_a_stage_that_was_not_enabled_is_refused() -> None:
    error = refused(
        lambda: editor(RecordingFiles()).disable(lock_with(text()), "plain_style", "outline"),
        "SKILL_NOT_ENABLED",
    )
    assert "not enabled for stage 'outline'" in error.message


def test_disabling_a_skill_that_is_not_locked_is_refused() -> None:
    refused(
        lambda: editor(RecordingFiles()).disable(SkillLock(), "plain_style", "outline"),
        "SKILL_UNKNOWN",
    )


# ---------------------------------------------------------------------------------- remove
def test_removing_unlocks_the_skill_and_deletes_its_copy() -> None:
    files = RecordingFiles({COPY: text()})
    other = locked(text("other_one"), "other_one")
    lock = SkillLock((locked(text()), other))
    changed = editor(files).remove(lock, FOLDER, "plain_style")
    assert changed.names() == ("other_one",)
    assert files.removed == [COPY] and COPY not in files.files


def test_removing_a_skill_that_is_not_locked_deletes_nothing() -> None:
    files = RecordingFiles({COPY: text()})
    refused(lambda: editor(files).remove(SkillLock(), FOLDER, "plain_style"), "SKILL_UNKNOWN")
    assert files.removed == [] and COPY in files.files


# ----------------------------------------------------------------------------- add_bytes
def test_adding_bytes_locks_their_hash_keeps_them_and_enables_nothing() -> None:
    data = text()
    files = RecordingFiles()
    added = editor(files).add_bytes(SkillLock(), FOLDER, "plain_style", data, replace=False)
    assert added.lock.entry("plain_style") == SkillLockEntry(
        "plain_style", 2, hashlib.sha256(data).hexdigest(), ()
    )
    assert added.skill.identifier() == "plain_style@2"
    assert files.writes == [(COPY, data, False)]


def test_adding_bytes_for_a_skill_that_is_locked_is_refused_unless_asked() -> None:
    files = RecordingFiles()
    lock = SkillLock((locked(text(), stages=("outline",)),))
    error = refused(
        lambda: editor(files).add_bytes(lock, FOLDER, "plain_style", text(), False),
        "SKILL_ALREADY_LOCKED",
        409,
    )
    assert "use --replace" in error.message and files.writes == []
    again = text(version=3)
    added = editor(files).add_bytes(lock, FOLDER, "plain_style", again, replace=True)
    found = added.lock.entry("plain_style")
    assert found is not None and found.stages == () and found.version == 3
    assert files.writes == [(COPY, again, True)]


def test_bytes_that_are_not_a_skill_are_refused_and_nothing_is_kept() -> None:
    files = RecordingFiles()
    refused(
        lambda: editor(files).add_bytes(SkillLock(), FOLDER, "plain_style", b"not = = toml", False),
        "SKILL_INVALID",
    )
    refused(
        lambda: editor(files).add_bytes(SkillLock(), FOLDER, "other_name", text(), False),
        "SKILL_INVALID",
    )
    assert files.writes == []
