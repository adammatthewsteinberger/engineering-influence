# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""TemporaryScreenplayEpubWriter: the archive is written with a fixed date, checked where it was written, and returned as bytes."""

from pathlib import Path

from engineering_influence.infrastructure.epub.temporary_screenplay_epub_writer import (
    TemporaryScreenplayEpubWriter,
)
from engineering_influence.interfaces.epub_package_interface import EpubPackageInterface
from engineering_influence.interfaces.epubcheck_interface import EpubcheckInterface


class Package(EpubPackageInterface):
    """Records the path and the date it was asked to write, and writes the bytes it was given."""

    def __init__(self) -> None:
        self.calls: list[tuple[Path, tuple[tuple[str, bytes, bool], ...], tuple[int, ...]]] = []

    def read_members(self, path: Path) -> dict[str, bytes]:
        raise NotImplementedError

    def write_members(self, path, entries, date_time) -> None:  # type: ignore[no-untyped-def]
        self.calls.append((path, tuple(entries), date_time))
        path.write_bytes(b"ARCHIVE")


class Validator(EpubcheckInterface):
    """Looks at the archive it is given, and reports the findings it was built with."""

    def __init__(self, findings: list[str]) -> None:
        self.findings = findings
        self.seen: list[Path] = []

    def run(self, path: Path) -> list[str]:
        self.seen.append(path)
        assert path.read_bytes() == b"ARCHIVE"
        return self.findings


def test_the_archive_is_written_with_a_fixed_date_and_returned_with_no_findings() -> None:
    package, validator = Package(), Validator([])
    entries = (("mimetype", b"application/epub+zip", True),)
    data, problems = TemporaryScreenplayEpubWriter(package, validator).write(entries)
    assert data == b"ARCHIVE"
    assert problems == ()
    assert package.calls[0][1] == entries
    assert package.calls[0][2] == (2000, 1, 1, 0, 0, 0)


def test_the_findings_are_returned_and_the_scratch_folder_is_removed() -> None:
    package, validator = Package(), Validator(["ERROR: bad"])
    _, problems = TemporaryScreenplayEpubWriter(package, validator).write(())
    assert problems == ("ERROR: bad",)
    assert not validator.seen[0].exists()
    assert not validator.seen[0].parent.exists()
