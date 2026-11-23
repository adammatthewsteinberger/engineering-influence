# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ManuscriptAudit: whether a book passed, what was wrong, and the reports that say so."""

from typing import Any

import pytest

from engineering_influence.models.interfaces.manuscript_audit_interface import (
    ManuscriptAuditInterface,
)
from engineering_influence.models.manuscript_audit import ManuscriptAudit


def audit(**changes: Any) -> ManuscriptAudit:
    fields: dict[str, Any] = {
        "passed": True,
        "status": "pass",
        "errors": (),
        "warnings": ("missing-price: no price",),
        "files": (("release-readiness.json", b"{}"),),
    }
    return ManuscriptAudit(**{**fields, **changes})


def refused(**changes: Any) -> str:
    with pytest.raises((ValueError, TypeError)) as error:
        audit(**changes)
    return str(error.value)


def test_an_audit_says_whether_the_book_passed_and_what_it_found() -> None:
    made = audit()
    assert isinstance(made, ManuscriptAuditInterface)
    assert made.passed and made.warnings == ("missing-price: no price",)
    assert made.files == (("release-readiness.json", b"{}"),)


def test_a_book_with_errors_did_not_pass_but_may_fail_without_listing_them() -> None:
    assert refused(passed=True, errors=("bad",)) == "an audit with errors did not pass"
    assert audit(passed=False, status="fail", errors=("bad",)).errors == ("bad",)
    assert audit(passed=False, status="fail").errors == ()


def test_the_status_is_a_word_and_passed_is_a_boolean() -> None:
    assert refused(status=" ") == "an audit says whether it passed and in what status"
    assert refused(passed=1) == "an audit says whether it passed and in what status"


def test_errors_and_warnings_are_tuples_of_real_messages() -> None:
    for field in ("errors", "warnings"):
        assert refused(**{field: ["x"]}) == f"the {field} are a tuple of messages"
        assert refused(**{field: (" ",)}) == f"the {field} are a tuple of messages"


def test_report_files_have_distinct_plain_names() -> None:
    assert refused(files=(("a.json", b""), ("a.json", b""))) == (
        "the report files are a tuple of distinct names"
    )
    assert refused(files=[("a.json", b"")]) == "the report files are a tuple of distinct names"
    for bad in ("", "dir/a.json", ".hidden"):
        assert (
            refused(files=((bad, b""),)) == "a report file has a plain name, with no folder in it"
        )
