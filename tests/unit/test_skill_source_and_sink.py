# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""FileSkillSource and NewFileSkillSink: read one plain file, write one new file, follow no link."""

import os
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.skills.file_skill_source import FileSkillSource
from engineering_influence.infrastructure.skills.new_file_skill_sink import NewFileSkillSink
from engineering_influence.interfaces.skill_sink_interface import SkillSinkInterface
from engineering_influence.interfaces.skill_source_interface import SkillSourceInterface

SOURCE = FileSkillSource()
SINK = NewFileSkillSink()


def refused(path: Path) -> str:
    with pytest.raises(ApplicationError) as error:
        SOURCE.read(path)
    assert (error.value.code, error.value.http_status) == ("SKILL_SOURCE_INVALID", 422)
    return error.value.message


def test_they_are_a_source_and_a_sink() -> None:
    assert isinstance(SOURCE, SkillSourceInterface) and isinstance(SINK, SkillSinkInterface)


def test_a_file_is_read_and_so_is_the_skill_md_in_a_folder(tmp_path: Path) -> None:
    (tmp_path / "SKILL.md").write_text("hello é", encoding="utf-8")
    assert SOURCE.read(tmp_path / "SKILL.md") == "hello é"
    assert SOURCE.read(tmp_path) == "hello é"
    other = tmp_path / "other.md"
    other.write_text("named differently", encoding="utf-8")
    assert SOURCE.read(other) == "named differently"


def test_a_missing_path_and_a_folder_without_a_skill_md_are_refused(tmp_path: Path) -> None:
    assert "is not a SKILL.md file or a folder that holds one" in refused(tmp_path / "none.md")
    assert "is not a SKILL.md file" in refused(tmp_path)


def test_a_link_is_never_followed_for_the_file_or_the_folder(tmp_path: Path) -> None:
    real = tmp_path / "real.md"
    real.write_text("secret", encoding="utf-8")
    link = tmp_path / "link.md"
    os.symlink(real, link)
    assert "is not a SKILL.md file" in refused(link)
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "SKILL.md").write_text("x", encoding="utf-8")
    folder_link = tmp_path / "folder_link"
    os.symlink(folder, folder_link)
    assert "is not a SKILL.md file" in refused(folder_link)
    inside = tmp_path / "inside"
    inside.mkdir()
    os.symlink(real, inside / "SKILL.md")
    assert "is not a SKILL.md file" in refused(inside)


def test_the_size_limit_is_two_hundred_and_fifty_six_kibibytes() -> None:
    assert FileSkillSource.MAX_BYTES == 256 * 1024


def test_a_file_may_be_exactly_the_size_limit_and_not_a_byte_more(tmp_path: Path) -> None:
    path = tmp_path / "SKILL.md"
    path.write_bytes(b"a" * FileSkillSource.MAX_BYTES)
    assert len(SOURCE.read(path)) == FileSkillSource.MAX_BYTES
    path.write_bytes(b"a" * (FileSkillSource.MAX_BYTES + 1))
    assert f"larger than {FileSkillSource.MAX_BYTES} bytes" in refused(path)


def test_text_that_is_not_utf_8_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "SKILL.md"
    path.write_bytes(b"caf\xe9")
    assert "is not UTF-8 text" in refused(path)


def test_a_new_file_is_written_with_its_parents(tmp_path: Path) -> None:
    target = tmp_path / "deep" / "er" / "skill.toml"
    SINK.write_new(target, b"name = 'x'\n")
    assert target.read_bytes() == b"name = 'x'\n"


def test_a_file_that_is_already_there_is_not_replaced(tmp_path: Path) -> None:
    target = tmp_path / "skill.toml"
    target.write_text("mine", encoding="utf-8")
    with pytest.raises(ApplicationError) as error:
        SINK.write_new(target, b"theirs")
    assert (error.value.code, error.value.http_status) == ("SKILL_TARGET_EXISTS", 409)
    assert str(target) in error.value.message
    assert target.read_text(encoding="utf-8") == "mine"


def test_a_link_at_the_target_is_not_written_through(tmp_path: Path) -> None:
    elsewhere = tmp_path / "elsewhere.txt"
    elsewhere.write_text("untouched", encoding="utf-8")
    link = tmp_path / "skill.toml"
    os.symlink(elsewhere, link)
    with pytest.raises(ApplicationError):
        SINK.write_new(link, b"x")
    assert elsewhere.read_text(encoding="utf-8") == "untouched"
