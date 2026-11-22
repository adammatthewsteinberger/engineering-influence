# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""TomlSkillLockStore: a lock that reads strictly, writes the same bytes every time, and is never half written."""

from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.skills.toml_skill_lock_store import TomlSkillLockStore
from engineering_influence.interfaces.skill_lock_store_interface import SkillLockStoreInterface
from engineering_influence.models.skill_lock import SkillLock
from engineering_influence.models.skill_lock_entry import SkillLockEntry

A, B = "a" * 64, "b" * 64


def entry(name: str, sha: str = A, stages: tuple[str, ...] = ()) -> SkillLockEntry:
    return SkillLockEntry(name, 2, sha, stages)


def store() -> TomlSkillLockStore:
    return TomlSkillLockStore()


def loading(tmp_path: Path, text: str) -> ApplicationError:
    path = tmp_path / "lock.toml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ApplicationError) as error:
        store().load(path)
    assert error.value.code == "SKILL_LOCK_INVALID" and error.value.http_status == 422
    return error.value


def block(**changes: str) -> str:
    fields = {"name": '"plain"', "version": "2", "sha256": f'"{A}"', "stages": '["outline"]'}
    return "[[skill]]\n" + "".join(f"{k} = {v}\n" for k, v in {**fields, **changes}.items())


def test_it_is_a_skill_lock_store() -> None:
    assert isinstance(store(), SkillLockStoreInterface)


def test_a_missing_file_is_no_lock() -> None:
    assert store().load(Path("/nonexistent/ei-skills.lock.toml")) is None


def test_a_lock_survives_a_save_and_a_load(tmp_path: Path) -> None:
    path = tmp_path / "lock.toml"
    lock = SkillLock((entry("zed", B, ("outline", "research")), entry("alpha")))
    store().save(path, lock)
    loaded = store().load(path)
    assert loaded is not None and set(loaded.entries) == set(lock.entries)


def test_the_layout_is_fixed_with_skills_in_name_order(tmp_path: Path) -> None:
    path = tmp_path / "lock.toml"
    store().save(path, SkillLock((entry("zed", stages=("outline",)), entry("alpha"))))
    text = path.read_text(encoding="utf-8")
    assert text.startswith("# Installed skills: prompt text a person chose, never code.")
    assert text.index('name = "alpha"') < text.index('name = "zed"')
    assert text.count("[[skill]]") == 2 and text.count("version = 1\n") == 1
    assert f'sha256 = "{A}"\nstages = ["outline"]\n' in text
    assert "stages = []\n" in text and "version = 2\n" in text


def test_two_saves_of_the_same_lock_give_the_same_bytes_and_leave_no_temporary_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "lock.toml"
    lock = SkillLock((entry("b", stages=("research",)), entry("a")))
    store().save(path, lock)
    first = path.read_bytes()
    store().save(path, SkillLock((entry("a"), entry("b", stages=("research",)))))
    assert path.read_bytes() == first
    assert sorted(item.name for item in tmp_path.iterdir()) == ["lock.toml"]


def test_an_empty_lock_is_a_valid_file(tmp_path: Path) -> None:
    path = tmp_path / "lock.toml"
    store().save(path, SkillLock())
    loaded = store().load(path)
    assert loaded is not None and loaded.entries == ()


def test_a_file_that_cannot_be_read_is_an_error_that_names_it(tmp_path: Path) -> None:
    folder = tmp_path / "folder"
    folder.mkdir()
    with pytest.raises(ApplicationError, match=r"cannot read .*folder.*IsADirectoryError"):
        store().load(folder)
    path = tmp_path / "binary.toml"
    path.write_bytes(b"\xff\xfe")
    with pytest.raises(ApplicationError, match="UnicodeDecodeError"):
        store().load(path)


def test_text_that_is_not_toml_is_refused(tmp_path: Path) -> None:
    assert "is not valid TOML" in loading(tmp_path, "version = ").message


def test_an_unknown_top_level_key_is_refused(tmp_path: Path) -> None:
    assert "unknown top-level key 'extra'" in loading(tmp_path, "version = 1\nextra = 1\n").message


@pytest.mark.parametrize("version", ["", "version = 2\n", 'version = "1"\n', "version = true\n"])
def test_a_version_this_does_not_read_is_refused(tmp_path: Path, version: str) -> None:
    assert "this reads 1" in loading(tmp_path, version).message


def test_skill_entries_must_be_a_list_of_tables(tmp_path: Path) -> None:
    assert "not a list of tables" in loading(tmp_path, "version = 1\n[skill]\nname = 'x'\n").message
    assert "skill #1 (?) is not a table" in loading(tmp_path, "version = 1\nskill = [1]\n").message


def test_an_entry_with_an_unknown_or_missing_key_is_refused_and_named(tmp_path: Path) -> None:
    message = loading(tmp_path, "version = 1\n" + block() + 'command = "x"\n').message
    assert "skill #1 (plain) has an unknown key 'command'" in message
    text = "version = 1\n[[skill]]\nname = 'plain'\nversion = 2\nsha256 = 'x'\n"
    assert "skill #1 (plain) is missing 'stages'" in loading(tmp_path, text).message
    assert (
        "skill #1 (?) is missing 'name'"
        in loading(
            tmp_path, "version = 1\n[[skill]]\nversion = 2\nsha256 = 'x'\nstages = []\n"
        ).message
    )


def test_stages_must_be_a_list(tmp_path: Path) -> None:
    text = "version = 1\n" + block(stages='"outline"')
    assert "skill #1 (plain) has stages that are not a list" in loading(tmp_path, text).message


def test_what_the_model_refuses_is_an_error_that_names_the_entry(tmp_path: Path) -> None:
    for changes, expected in (
        ({"sha256": '"abc"'}, "64 lowercase hex"),
        ({"version": '"2"'}, "version that is not a whole number"),
        ({"name": '"Plain"'}, "locked skill's name"),
        ({"stages": '["Outline"]'}, "not a stage name"),
        ({"stages": "[3]"}, "not a stage name"),
        ({"stages": '["research", "outline"]'}, "once each, in order"),
    ):
        message = loading(tmp_path, "version = 1\n" + block(**changes)).message
        assert expected in message and message.startswith("skill #1 (")


def test_a_lock_the_model_refuses_as_a_whole_is_an_error(tmp_path: Path) -> None:
    text = "version = 1\n" + block() + block()
    assert "share a name" in loading(tmp_path, text).message
    crowd = "".join(block(name=f'"skill_{n}"') for n in range(5))
    assert "the most is 4" in loading(tmp_path, "version = 1\n" + crowd).message


def test_a_name_with_odd_characters_is_written_safely(tmp_path: Path) -> None:
    quoted = TomlSkillLockStore._quote('a"b\\c\n\x7f')
    assert quoted == '"a\\"b\\\\c\\u000a\\u007f"'


def test_a_stale_temporary_link_is_never_written_through(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere.txt"
    elsewhere.write_text("untouched", encoding="utf-8")
    (tmp_path / ".lock.toml.tmp").symlink_to(elsewhere)
    store().save(tmp_path / "lock.toml", SkillLock((entry("a"),)))
    assert elsewhere.read_text(encoding="utf-8") == "untouched"
    loaded = store().load(tmp_path / "lock.toml")
    assert loaded is not None and loaded.names() == ("a",)
    assert sorted(item.name for item in tmp_path.iterdir()) == ["elsewhere.txt", "lock.toml"]
