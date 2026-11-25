# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""SkillLockVerifier: a skill is used only if its file is the one whose hash was locked."""

import hashlib
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.skills.toml_skill_parser import TomlSkillParser
from engineering_influence.interfaces.skill_files_interface import SkillFilesInterface
from engineering_influence.models.skill_lock import SkillLock
from engineering_influence.models.skill_lock_entry import SkillLockEntry
from engineering_influence.services.interfaces.skill_lock_verifier_interface import (
    SkillLockVerifierInterface,
)
from engineering_influence.services.skill_lock_verifier import SkillLockVerifier

FOLDER = Path("/project/skills")


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


def verifier(files: MemoryFiles) -> SkillLockVerifier:
    return SkillLockVerifier(files, TomlSkillParser())


def test_it_is_a_skill_lock_verifier() -> None:
    assert isinstance(verifier(MemoryFiles()), SkillLockVerifierInterface)


def test_a_skill_that_is_the_locked_text_is_returned() -> None:
    data = text()
    files = MemoryFiles({FOLDER / "plain_style.toml": data})
    found = verifier(files).skill(locked(data, stages=("outline",)), FOLDER)
    assert found.identifier() == "plain_style@2" and found.part("outline")
    assert files.reads == [FOLDER / "plain_style.toml"]


def test_a_skill_that_is_enabled_is_checked_and_one_that_is_not_is_never_read() -> None:
    on, off = text("on_skill"), text("off_skill")
    files = MemoryFiles({FOLDER / "on_skill.toml": on, FOLDER / "off_skill.toml": off})
    lock = SkillLock((locked(off, "off_skill"), locked(on, "on_skill", stages=("outline",))))
    found = verifier(files).verified(lock, FOLDER)
    assert [skill.name for skill in found] == ["on_skill"]
    assert files.reads == [FOLDER / "on_skill.toml"]


def test_verified_skills_come_back_in_name_order() -> None:
    data = {name: text(name) for name in ("zed", "alpha", "mid")}
    files = MemoryFiles({FOLDER / f"{name}.toml": body for name, body in data.items()})
    lock = SkillLock(tuple(locked(body, name, stages=("outline",)) for name, body in data.items()))
    assert [skill.name for skill in verifier(files).verified(lock, FOLDER)] == [
        "alpha",
        "mid",
        "zed",
    ]


def test_a_lock_with_nothing_enabled_verifies_to_nothing_and_reads_nothing() -> None:
    files = MemoryFiles()
    assert verifier(files).verified(SkillLock((locked(text()),)), FOLDER) == ()
    assert verifier(files).verified(SkillLock(), FOLDER) == ()
    assert files.reads == []


def mismatch(action: object) -> ApplicationError:
    with pytest.raises(ApplicationError) as error:
        action()  # type: ignore[operator]
    assert error.value.code == "SKILL_LOCK_MISMATCH" and error.value.http_status == 503
    return error.value


def test_a_missing_file_is_a_mismatch_that_names_the_path() -> None:
    entry = locked(text(), stages=("outline",))
    error = mismatch(lambda: verifier(MemoryFiles()).skill(entry, FOLDER))
    assert error.message == f"skill 'plain_style': {FOLDER / 'plain_style.toml'} is missing"


def test_a_file_that_changed_by_one_character_is_refused_before_it_is_parsed() -> None:
    entry = locked(text(), stages=("outline",))
    changed = text(outline="Prefer short sentences!", research="Say where you read it.")
    error = mismatch(
        lambda: verifier(MemoryFiles({FOLDER / "plain_style.toml": changed})).skill(entry, FOLDER)
    )
    assert "has changed since it was locked" in error.message
    assert "ei skills add --replace" in error.message and "plain_style.toml" in error.message


def test_a_file_that_cannot_be_read_is_a_mismatch_with_the_reason() -> None:
    files = MemoryFiles()
    path = FOLDER / "plain_style.toml"
    files.broken[path] = ApplicationError(code="SKILL_FILE_UNUSABLE", message="a link, so no")
    error = mismatch(lambda: verifier(files).skill(locked(text()), FOLDER))
    assert error.message == "a link, so no"


def test_a_file_whose_hash_matches_but_is_not_a_skill_is_a_mismatch_with_the_reason() -> None:
    junk = b"this is = = not toml"
    files = MemoryFiles({FOLDER / "plain_style.toml": junk})
    error = mismatch(lambda: verifier(files).skill(locked(junk), FOLDER))
    assert error.message.startswith("skill 'plain_style': it is not valid TOML")


def test_a_version_that_disagrees_with_the_lock_is_refused() -> None:
    data = text(version=3)
    files = MemoryFiles({FOLDER / "plain_style.toml": data})
    error = mismatch(lambda: verifier(files).skill(locked(data, version=2), FOLDER))
    assert error.message == ("skill 'plain_style': its file is version 3, but the lock has 2")


def test_a_stage_the_lock_enables_that_the_skill_has_no_text_for_is_refused() -> None:
    data = text()
    files = MemoryFiles({FOLDER / "plain_style.toml": data})
    error = mismatch(
        lambda: verifier(files).skill(locked(data, stages=("brief", "outline")), FOLDER)
    )
    assert error.message == (
        "skill 'plain_style': the lock enables it for ['brief'], which it has no text for"
    )


def test_every_problem_with_an_enabled_skill_is_reported_at_once() -> None:
    good, bad = text("good_one"), text("bad_one")
    files = MemoryFiles({FOLDER / "good_one.toml": good, FOLDER / "bad_one.toml": b"changed"})
    lock = SkillLock(
        (
            locked(good, "good_one", stages=("outline",)),
            locked(bad, "bad_one", stages=("outline",)),
            locked(text("gone_one"), "gone_one", stages=("research",)),
        )
    )
    error = mismatch(lambda: verifier(files).verified(lock, FOLDER))
    assert "; skill 'gone_one'" in error.message
    assert error.message.index("bad_one") < error.message.index("gone_one")
    assert "good_one" not in error.message


def test_problems_covers_every_locked_skill_enabled_or_not_in_name_order() -> None:
    ok = text("fine_one")
    files = MemoryFiles({FOLDER / "fine_one.toml": ok, FOLDER / "zed_one.toml": b"changed"})
    lock = SkillLock(
        (
            locked(text("zed_one"), "zed_one"),
            locked(ok, "fine_one"),
            locked(text("alpha_one"), "alpha_one", stages=("outline",)),
        )
    )
    found = verifier(files).problems(lock, FOLDER)
    assert len(found) == 2
    assert "alpha_one" in found[0] and "is missing" in found[0]
    assert "zed_one" in found[1] and "has changed" in found[1]
    assert verifier(files).problems(SkillLock((locked(ok, "fine_one"),)), FOLDER) == ()
