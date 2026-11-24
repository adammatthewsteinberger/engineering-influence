"""The builder lays the book out in a scratch folder, publishes and packages it there, and reads the files back."""

from pathlib import Path
from typing import Any

import pytest

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.infrastructure.build.temp_project_manuscript_builder import (
    TempProjectManuscriptBuilder,
)
from engineering_influence.interfaces.book_publisher_interface import BookPublisherInterface

FILES = {"books/herbs.toml": b"title = 'Herbs'", "src/chapter_01.md": b"# One"}


def report(**changes: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "status": "pass",
        "manuscript_audit": {"issues": [], "warnings": []},
        "release_readiness": {"findings": []},
        "steps": [
            {"name": "pdf", "status": "pass", "stdout_tail": "built"},
            {"name": "epub", "status": "pass", "stdout_tail": "built"},
        ],
    }
    values.update(changes)
    return values


class Publisher(BookPublisherInterface):
    """Writes what the real pipeline writes into the project, and records how it was called."""

    def __init__(
        self, root: Path, result: dict[str, Any], passed: bool, refuse: str | None = None
    ) -> None:
        self.root = root
        self.result = result
        self.passed = passed
        self.refuse = refuse
        self.writes = True
        self.seen: dict[str, Any] = {}

    def publish(
        self, slug: str, *, no_render: bool = False, strict_release: bool = False
    ) -> tuple[dict[str, Any], bool]:
        self.seen["publish"] = (slug, no_render, strict_release)
        self.seen["project"] = sorted(
            str(p.relative_to(self.root)) for p in self.root.rglob("*") if p.is_file()
        )
        if self.writes:
            release = self.root / "build" / slug / "release"
            release.mkdir(parents=True)
            (release / "publication-report.json").write_bytes(b'{"status": "x"}')
            (release / "pdf.log").write_bytes(b"pdf log")
            (release / ".hidden").write_bytes(b"skip me")
            (release / "folder").mkdir()
        return self.result, self.passed

    def package(self, slug: str) -> str:
        self.seen["package"] = slug
        kdp = self.root / "build" / slug / "release" / "kdp"
        kdp.mkdir()
        (kdp / "listing.md").write_bytes(b"# Listing")
        (kdp / "herbs.pdf").write_bytes(b"%PDF")
        if self.refuse:  # the packager had already written files when it refused
            raise BookBuildError(self.refuse)
        return "packaged"


def builder(
    result: dict[str, Any],
    passed: bool,
    holder: list[Publisher],
    refuse: str | None = None,
    **options: Any,
) -> TempProjectManuscriptBuilder:
    def make(root: Path) -> Publisher:
        publisher = Publisher(root, result, passed, refuse)
        holder.append(publisher)
        return publisher

    return TempProjectManuscriptBuilder(make, **options)


def test_the_files_are_laid_out_as_a_project_before_the_book_is_published() -> None:
    holder: list[Publisher] = []
    builder(report(), True, holder).build(FILES, "herbs")
    assert holder[0].seen["project"] == ["books/herbs.toml", "src/chapter_01.md"]


def test_a_passing_book_is_packaged_and_its_bundle_and_evidence_are_returned() -> None:
    holder: list[Publisher] = []
    result = builder(report(), True, holder).build(FILES, "herbs")
    assert result.passed and result.status == "pass" and result.errors == ()
    assert holder[0].seen["package"] == "herbs"
    assert dict(result.book) == {"listing.md": b"# Listing", "herbs.pdf": b"%PDF"}
    assert dict(result.reports) == {
        "publication-report.json": b'{"status": "x"}',
        "pdf.log": b"pdf log",
    }
    assert result.steps == (("pdf", "pass"), ("epub", "pass"))


def test_the_warnings_of_the_audit_and_the_release_check_are_returned() -> None:
    holder: list[Publisher] = []
    result = builder(
        report(
            manuscript_audit={"issues": [], "warnings": [{"code": "thin", "message": "short"}]},
            release_readiness={
                "findings": [{"severity": "warning", "code": "price", "message": "none"}]
            },
        ),
        True,
        holder,
    ).build(FILES, "herbs")
    assert result.warnings == ("thin: short", "price: none")


@pytest.mark.parametrize(
    ("options", "expected"),
    [({}, (False, False)), ({"no_render": True, "strict_release": True}, (True, True))],
)
def test_rendering_and_a_strict_release_are_options(
    options: dict[str, bool], expected: tuple[bool, bool]
) -> None:
    holder: list[Publisher] = []
    builder(report(), True, holder, **options).build(FILES, "herbs")
    assert holder[0].seen["publish"] == ("herbs", *expected)


def test_a_book_that_fails_a_gate_is_not_packaged_and_says_why() -> None:
    holder: list[Publisher] = []
    failed = report(
        status="fail",
        manuscript_audit={
            "issues": [{"code": "word-count", "message": "too short"}],
            "warnings": [],
        },
        release_readiness={
            "findings": [{"severity": "error", "code": "keywords", "message": "need seven"}]
        },
        steps=[
            {"name": "pdf", "status": "fail", "stdout_tail": "x" * 600 + "no font Garamond\n  "},
            {"name": "epub", "status": "pass", "stdout_tail": ""},
        ],
        problems=["blank pages: 4, 5, 6"],
    )
    result = builder(failed, False, holder).build(FILES, "herbs")
    assert not result.passed and result.status == "fail" and result.book == ()
    assert "package" not in holder[0].seen
    assert result.errors[:2] == ("word-count: too short", "keywords: need seven")
    assert result.errors[2].startswith("step pdf failed: ") and result.errors[2].endswith(
        "no font Garamond"
    )
    assert len(result.errors[2]) < 600
    assert result.errors[3] == "blank pages: 4, 5, 6"
    assert dict(result.reports)["publication-report.json"] == b'{"status": "x"}'


def test_a_book_the_packager_refuses_does_not_pass() -> None:
    holder: list[Publisher] = []
    result = builder(report(), True, holder, refuse="[herbs] the release check fails").build(
        FILES, "herbs"
    )
    assert not result.passed and result.book == ()
    assert result.errors == ("[herbs] the release check fails",)


def test_a_pipeline_that_wrote_nothing_returns_no_files() -> None:
    class Silent(Publisher):
        def __init__(self, root: Path) -> None:
            super().__init__(root, report(status="fail"), False)
            self.writes = False

    result = TempProjectManuscriptBuilder(Silent).build(FILES, "herbs")
    assert (result.reports, result.book) == ((), ())
    assert not result.passed


def test_a_failure_with_no_message_still_says_what_happened() -> None:
    holder: list[Publisher] = []
    result = builder(report(status="fail"), False, holder).build(FILES, "herbs")
    assert result.errors == ("the publication pipeline reported 'fail'",)


def test_a_path_that_leaves_the_project_is_refused_and_nothing_is_published() -> None:
    holder: list[Publisher] = []
    with pytest.raises(ValueError, match="would leave the project"):
        builder(report(), True, holder).build({"../escape.md": b"x"}, "herbs")
    assert holder == []


def test_nothing_of_the_book_is_left_on_disk() -> None:
    holder: list[Publisher] = []
    builder(report(), True, holder).build(FILES, "herbs")
    assert not holder[0].root.exists()
