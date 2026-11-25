# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""DirectorySkillFiles: plain files only, never followed through a link, never large, never half written."""

import os
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.skills.directory_skill_files import DirectorySkillFiles
from engineering_influence.interfaces.skill_files_interface import SkillFilesInterface

LIMIT = DirectorySkillFiles.MAX_BYTES


def files() -> DirectorySkillFiles:
    return DirectorySkillFiles()


def refusal(action: object) -> ApplicationError:
    with pytest.raises(ApplicationError) as error:
        action()  # type: ignore[operator]
    return error.value


def test_it_is_a_skill_files_port() -> None:
    assert isinstance(files(), SkillFilesInterface)
    assert LIMIT == 256 * 1024


def test_a_missing_file_is_none_and_a_plain_file_is_its_bytes(tmp_path: Path) -> None:
    assert files().read(tmp_path / "none.toml") is None
    (tmp_path / "a.toml").write_bytes(b"name = 'a'\n")
    assert files().read(tmp_path / "a.toml") == b"name = 'a'\n"


def test_a_file_exactly_at_the_limit_is_read_and_one_byte_more_is_refused(tmp_path: Path) -> None:
    (tmp_path / "ok.toml").write_bytes(b"x" * LIMIT)
    assert files().read(tmp_path / "ok.toml") == b"x" * LIMIT
    (tmp_path / "big.toml").write_bytes(b"x" * (LIMIT + 1))
    error = refusal(lambda: files().read(tmp_path / "big.toml"))
    assert error.code == "SKILL_FILE_UNUSABLE" and error.http_status == 422
    assert f"longer than {LIMIT} bytes" in error.message and "big.toml" in error.message


def test_a_link_is_refused_and_so_is_a_link_to_nowhere(tmp_path: Path) -> None:
    (tmp_path / "real.toml").write_bytes(b"text")
    (tmp_path / "link.toml").symlink_to(tmp_path / "real.toml")
    (tmp_path / "dangling.toml").symlink_to(tmp_path / "nowhere.toml")
    for name in ("link.toml", "dangling.toml"):
        error = refusal(lambda name=name: files().read(tmp_path / name))  # type: ignore[misc]
        assert error.code == "SKILL_FILE_UNUSABLE" and name in error.message


def test_a_folder_is_not_a_skill(tmp_path: Path) -> None:
    (tmp_path / "folder.toml").mkdir()
    error = refusal(lambda: files().read(tmp_path / "folder.toml"))
    assert "not a plain file" in error.message


def test_a_path_that_cannot_be_opened_is_refused_with_the_reason(tmp_path: Path) -> None:
    (tmp_path / "plain").write_bytes(b"x")
    error = refusal(lambda: files().read(tmp_path / "plain" / "skill.toml"))
    assert error.code == "SKILL_FILE_UNUSABLE" and "Not a directory" in error.message


def test_a_write_makes_the_folder_and_leaves_no_temporary_file(tmp_path: Path) -> None:
    target = tmp_path / "skills" / "plain.toml"
    files().write(target, b"hello", replace=False)
    assert target.read_bytes() == b"hello"
    assert sorted(path.name for path in target.parent.iterdir()) == ["plain.toml"]


def test_an_existing_file_is_replaced_only_when_asked(tmp_path: Path) -> None:
    target = tmp_path / "plain.toml"
    target.write_bytes(b"old")
    error = refusal(lambda: files().write(target, b"new", replace=False))
    assert error.code == "SKILL_FILE_EXISTS" and error.http_status == 409
    assert "--replace" in error.message and target.read_bytes() == b"old"
    files().write(target, b"new", replace=True)
    assert target.read_bytes() == b"new"


def test_a_link_in_the_way_counts_as_a_file_and_is_replaced_not_followed(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere.txt"
    elsewhere.write_bytes(b"untouched")
    target = tmp_path / "plain.toml"
    target.symlink_to(elsewhere)
    assert refusal(lambda: files().write(target, b"new", replace=False)).code == "SKILL_FILE_EXISTS"
    files().write(target, b"new", replace=True)
    assert not target.is_symlink() and target.read_bytes() == b"new"
    assert elsewhere.read_bytes() == b"untouched"


def test_a_stale_temporary_link_is_not_written_through(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere.txt"
    elsewhere.write_bytes(b"untouched")
    (tmp_path / ".plain.toml.tmp").symlink_to(elsewhere)
    files().write(tmp_path / "plain.toml", b"new", replace=False)
    assert elsewhere.read_bytes() == b"untouched"
    assert (tmp_path / "plain.toml").read_bytes() == b"new"
    assert not os.path.lexists(tmp_path / ".plain.toml.tmp")


def test_a_write_over_the_limit_is_refused_before_anything_is_written(tmp_path: Path) -> None:
    files().write(tmp_path / "ok.toml", b"x" * LIMIT, replace=False)
    error = refusal(lambda: files().write(tmp_path / "big.toml", b"x" * (LIMIT + 1), False))
    assert error.code == "SKILL_FILE_UNUSABLE"
    assert not (tmp_path / "big.toml").exists()


def test_removing_deletes_the_file_and_a_missing_one_is_fine(tmp_path: Path) -> None:
    (tmp_path / "a.toml").write_bytes(b"x")
    files().remove(tmp_path / "a.toml")
    assert not (tmp_path / "a.toml").exists()
    files().remove(tmp_path / "a.toml")


def test_removing_a_link_removes_the_link_and_not_what_it_points_at(tmp_path: Path) -> None:
    (tmp_path / "real.toml").write_bytes(b"x")
    (tmp_path / "link.toml").symlink_to(tmp_path / "real.toml")
    files().remove(tmp_path / "link.toml")
    assert not os.path.lexists(tmp_path / "link.toml")
    assert (tmp_path / "real.toml").read_bytes() == b"x"


def test_the_size_cap_can_be_given_and_is_enforced_on_both_sides(tmp_path: Path) -> None:
    small = DirectorySkillFiles(10)
    (tmp_path / "ok.toml").write_bytes(b"x" * 10)
    assert small.read(tmp_path / "ok.toml") == b"x" * 10
    (tmp_path / "big.toml").write_bytes(b"x" * 11)
    assert "longer than 10 bytes" in refusal(lambda: small.read(tmp_path / "big.toml")).message
    small.write(tmp_path / "new.toml", b"x" * 10, replace=False)
    assert (
        "longer than 10 bytes"
        in refusal(lambda: small.write(tmp_path / "new2.toml", b"x" * 11, False)).message
    )
    assert not (tmp_path / "new2.toml").exists()
    assert DirectorySkillFiles().read(tmp_path / "big.toml") == b"x" * 11


def test_a_file_may_be_at_least_one_byte_long() -> None:
    with pytest.raises(ValueError, match="at least one byte"):
        DirectorySkillFiles(0)
    assert DirectorySkillFiles(1).read(Path("/nonexistent/none.toml")) is None
