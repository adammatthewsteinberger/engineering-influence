"""The adapter that reads a book project's files."""

from pathlib import Path

from engineering_influence.infrastructure.publishing.filesystem_manuscript_source import (
    FilesystemManuscriptSource,
)


def test_it_reports_existence_and_reads_utf8(tmp_path: Path) -> None:
    source = FilesystemManuscriptSource()
    (tmp_path / "a.md").write_text("héllo", encoding="utf-8")

    assert source.exists(tmp_path / "a.md") and not source.exists(tmp_path / "b.md")
    assert source.read_text(tmp_path / "a.md") == "héllo"


def test_it_can_replace_undecodable_bytes(tmp_path: Path) -> None:
    (tmp_path / "log.txt").write_bytes(b"ok \xff end")

    assert FilesystemManuscriptSource().read_text(tmp_path / "log.txt", errors="replace") == (
        "ok � end"
    )


def test_it_lists_only_the_markdown_files_in_a_directory(tmp_path: Path) -> None:
    for name in ("one.md", "two.md", "notes.txt"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "deep.md").write_text("x", encoding="utf-8")

    assert FilesystemManuscriptSource().markdown_names(tmp_path) == {"one.md", "two.md"}
