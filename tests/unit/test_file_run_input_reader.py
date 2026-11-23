# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""FileRunInputReader opens one plain text file, follows no link, and never cleans what it refuses."""

import os
from pathlib import Path

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.run_inputs.file_run_input_reader import (
    FileRunInputReader,
)
from engineering_influence.interfaces.run_input_reader_interface import RunInputReaderInterface

READER = FileRunInputReader()


def refused(path: Path, name: str | None = None) -> str:
    with pytest.raises(ApplicationError) as error:
        READER.read(path, name)
    assert (error.value.code, error.value.http_status) == ("RUN_INPUT_INVALID", 422)
    return error.value.message


def write(path: Path, data: bytes) -> Path:
    path.write_bytes(data)
    return path


def test_it_is_a_reader() -> None:
    assert isinstance(READER, RunInputReaderInterface)


@pytest.mark.parametrize("suffix", [".txt", ".md", ".markdown", ".TXT", ".Md"])
def test_a_text_file_becomes_an_input_named_for_the_file_unless_told_otherwise(
    tmp_path: Path, suffix: str
) -> None:
    made = READER.read(write(tmp_path / f"My Notes v2{suffix}", b"Hello\n"), None)
    assert (made.name, made.text, made.origin) == ("my-notes-v2", "Hello", "file")
    assert READER.read(write(tmp_path / f"x{suffix}", b"Hi"), "chosen").name == "chosen"


def test_line_endings_become_line_feeds_a_leading_bom_goes_and_the_ends_are_trimmed(
    tmp_path: Path,
) -> None:
    data = (chr(0xFEFF) + "\n  one\r\ntwo\rthree  \n\n").encode()
    assert READER.read(write(tmp_path / "a.txt", data), None).text == "one\ntwo\nthree"


def test_a_bom_that_is_not_leading_is_refused_not_cleaned(tmp_path: Path) -> None:
    data = ("one " + chr(0xFEFF) + " two").encode()
    assert "cannot be seen" in refused(write(tmp_path / "a.txt", data))


def test_a_file_that_is_not_text_a_link_a_folder_or_missing_is_refused(tmp_path: Path) -> None:
    assert "is not a plain file" in refused(tmp_path / "missing.txt")
    assert "is not a plain file" in refused(tmp_path)
    real = write(tmp_path / "real.txt", b"hello")
    os.symlink(real, tmp_path / "link.txt")
    assert "is not a plain file" in refused(tmp_path / "link.txt")
    assert "only .txt, .md, .markdown are read" in refused(write(tmp_path / "book.pdf", b"%PDF"))
    assert "is not a text file" in refused(write(tmp_path / "noextension", b"hello"))


def test_a_file_over_256_kib_or_not_utf8_or_blank_or_too_long_is_refused(tmp_path: Path) -> None:
    assert "larger than 262,144 bytes" in refused(
        write(tmp_path / "big.txt", b"a" * (256 * 1024 + 1))
    )
    assert READER.read(write(tmp_path / "ok.txt", b"a" * 40_000), None).text == "a" * 40_000
    assert "is not UTF-8 text" in refused(write(tmp_path / "bad.txt", b"\xff\xfe\x00"))
    assert "has text" in refused(write(tmp_path / "blank.txt", b" \n\t"))
    assert "the most is 50,000" in refused(write(tmp_path / "long.txt", b"a" * 60_000))


def test_a_file_exactly_256_kib_is_not_refused_for_size(tmp_path: Path) -> None:
    assert "the most is 50,000" in refused(write(tmp_path / "edge.txt", b"a" * (256 * 1024)))


def test_a_name_that_cannot_be_made_safe_is_refused_and_says_to_give_one(tmp_path: Path) -> None:
    assert "an input's name" in refused(write(tmp_path / "日本語.txt", b"hello"))
    assert "an input's name" in refused(write(tmp_path / "x.txt", b"hello"), "Bad Name")


def test_a_long_file_name_is_cut_to_the_limit(tmp_path: Path) -> None:
    made = READER.read(write(tmp_path / ("a" * 80 + ".txt"), b"hello"), None)
    assert made.name == "a" * 60


def test_dots_and_hyphens_at_the_ends_of_a_name_are_trimmed(tmp_path: Path) -> None:
    assert READER.read(write(tmp_path / "-.notes-.txt", b"hello"), None).name == "notes"
