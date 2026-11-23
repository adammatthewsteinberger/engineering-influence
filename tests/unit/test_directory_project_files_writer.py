# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""DirectoryProjectFilesWriter: a new folder gets every file or none, and nothing existing is overwritten."""

import os
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.export.directory_project_files_writer import (
    DirectoryProjectFilesWriter,
)
from engineering_influence.interfaces.project_files_writer_interface import (
    ProjectFilesWriterInterface,
)

WRITER = DirectoryProjectFilesWriter()
FILES = {"books/hive.toml": b"title = 'x'", "src/chapter_01.md": b"# One", "run/brief.md": b"b"}


def tree(root: Path) -> dict[str, bytes]:
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file()
    }


def refused(root: Path, files: dict[str, bytes] | None = None) -> ApplicationError:
    with pytest.raises(ApplicationError) as error:
        WRITER.write(root, FILES if files is None else files)
    assert (error.value.code, error.value.http_status) == ("EXPORT_TARGET_NOT_EMPTY", 409)
    return error.value


def test_it_is_a_project_files_writer() -> None:
    assert isinstance(WRITER, ProjectFilesWriterInterface)


def test_a_new_folder_gets_every_file_and_its_parents_are_made(tmp_path: Path) -> None:
    root = tmp_path / "deep" / "er" / "book"
    WRITER.write(root, FILES)
    assert tree(root) == FILES
    assert [p.name for p in root.parent.iterdir()] == ["book"]


def test_an_empty_existing_folder_is_filled(tmp_path: Path) -> None:
    root = tmp_path / "book"
    root.mkdir()
    WRITER.write(root, FILES)
    assert tree(root) == FILES


def test_a_folder_with_anything_in_it_is_refused_and_left_alone(tmp_path: Path) -> None:
    root = tmp_path / "book"
    root.mkdir()
    (root / "mine.txt").write_text("keep", encoding="utf-8")
    assert str(root) in refused(root).message
    assert tree(root) == {"mine.txt": b"keep"}


def test_a_file_where_the_folder_should_be_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "book"
    root.write_text("a file", encoding="utf-8")
    refused(root)
    assert root.read_text(encoding="utf-8") == "a file"


def test_a_link_where_the_folder_should_be_is_refused_even_if_it_points_at_an_empty_folder(
    tmp_path: Path,
) -> None:
    target = tmp_path / "elsewhere"
    target.mkdir()
    link = tmp_path / "book"
    os.symlink(target, link)
    refused(link)
    assert list(target.iterdir()) == []


@pytest.mark.parametrize(
    "name", ["", "/etc/passwd", "../escape", "a/../../escape", "a//b", "./a", "a\\b", "a/."]
)
def test_a_path_that_is_not_relative_and_inside_is_refused_before_anything_is_written(
    tmp_path: Path, name: str
) -> None:
    root = tmp_path / "book"
    with pytest.raises(ValueError, match="not a relative path inside the folder"):
        WRITER.write(root, {"ok.md": b"x", name: b"y"})
    assert not root.exists()
    assert list(tmp_path.iterdir()) == []


def test_a_failure_part_way_leaves_nothing_behind(tmp_path: Path) -> None:
    root = tmp_path / "out" / "book"
    with pytest.raises(OSError):
        WRITER.write(root, {"a": b"file", "a/b": b"needs a folder where the file is"})
    assert not root.exists()
    assert list((tmp_path / "out").iterdir()) == []


def test_files_are_not_written_through_a_link(tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("untouched", encoding="utf-8")
    root = tmp_path / "book"
    WRITER.write(root, {"x.md": b"new"})
    assert outside.read_text(encoding="utf-8") == "untouched"
