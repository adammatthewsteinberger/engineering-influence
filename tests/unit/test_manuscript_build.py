"""A build says whether the book passed, and carries the evidence and the files of the bundle."""

import pytest

from engineering_influence.models.manuscript_build import ManuscriptBuild

BOOK = (("listing.md", b"# Listing"), ("book.pdf", b"%PDF"))


def build(**changes: object) -> ManuscriptBuild:
    values: dict[str, object] = {
        "passed": True,
        "status": "pass",
        "errors": (),
        "warnings": ("price: no price",),
        "steps": (("pdf", "pass"),),
        "reports": (("publication-report.json", b"{}"),),
        "book": BOOK,
    }
    values.update(changes)
    return ManuscriptBuild(**values)  # type: ignore[arg-type]


def test_a_passing_build_keeps_its_files_steps_and_warnings() -> None:
    result = build()
    assert result.passed and result.book == BOOK
    assert result.steps == (("pdf", "pass"),)
    assert result.warnings == ("price: no price",)


def test_a_failing_build_may_have_no_bundle() -> None:
    result = build(passed=False, status="fail", errors=("step pdf failed",), book=())
    assert not result.passed and result.book == ()


def test_a_build_with_errors_did_not_pass() -> None:
    with pytest.raises(ValueError, match="errors did not pass"):
        build(errors=("boom",))


def test_a_build_that_passed_produced_the_files_of_the_book() -> None:
    with pytest.raises(ValueError, match="files of the book"):
        build(book=())


@pytest.mark.parametrize("status", ["", "  "])
def test_a_build_names_its_status(status: str) -> None:
    with pytest.raises(ValueError, match="status"):
        build(status=status)


def test_a_build_says_yes_or_no() -> None:
    with pytest.raises(ValueError, match="whether it passed"):
        build(passed="yes")


@pytest.mark.parametrize("label", ["errors", "warnings"])
def test_messages_are_a_tuple_of_text(label: str) -> None:
    with pytest.raises(ValueError, match=label):
        build(**{label: ["a list"]})
    with pytest.raises(ValueError, match=label):
        build(passed=False, status="fail", book=(), **{label: (" ",)})


@pytest.mark.parametrize("label", ["reports", "book"])
@pytest.mark.parametrize(
    "files",
    [
        (("a.md", b""), ("a.md", b"")),
        (("folder/a.md", b""),),
        ((".hidden", b""),),
        (("", b""),),
    ],
)
def test_files_have_distinct_plain_names(label: str, files: object) -> None:
    with pytest.raises(ValueError, match=label):
        build(passed=False, status="fail", errors=("x",), **{label: files})
