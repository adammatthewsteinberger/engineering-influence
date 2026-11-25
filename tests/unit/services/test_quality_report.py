"""quality-report.json: what the run recorded, what the build found, and the hash of every finished file."""

import hashlib
import json

from engineering_influence.models.manuscript_build import ManuscriptBuild
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.spend_summary import SpendSummary
from engineering_influence.services.quality_report import QualityReport

PDF = b"%PDF-1.7 the interior"


def passing() -> ManuscriptBuild:
    return ManuscriptBuild(
        True,
        "pass",
        (),
        ("price: no price",),
        (("pdf", "pass"), ("epub", "pass")),
        (("publication-report.json", b"{}"),),
        (("listing.md", b"# Listing\n"), ("herbs.pdf", PDF)),
    )


def failing() -> ManuscriptBuild:
    return ManuscriptBuild(
        False, "fail", ("step pdf failed: no font",), (), (("pdf", "fail"),), (), ()
    )


def test_a_passing_build_lists_each_file_with_its_size_and_hash() -> None:
    report = json.loads(QualityReport().render("herbs", (), passing()))
    assert (
        report["status"] == "pass" and report["slug"] == "herbs" and report["schema_version"] == 1
    )
    assert report["files"][1] == {
        "path": "book/herbs.pdf",
        "bytes": len(PDF),
        "sha256": hashlib.sha256(PDF).hexdigest(),
    }
    assert [item["path"] for item in report["files"]] == ["book/listing.md", "book/herbs.pdf"]
    assert report["warnings"] == ["price: no price"] and report["errors"] == []
    assert report["steps"] == [
        {"name": "pdf", "status": "pass"},
        {"name": "epub", "status": "pass"},
    ]


def test_a_failing_build_says_so_and_lists_no_files() -> None:
    report = json.loads(QualityReport().render("herbs", (), failing()))
    assert report["status"] == "fail" and report["files"] == []
    assert report["errors"] == ["step pdf failed: no font"]


def test_the_issues_the_run_recorded_are_carried_over() -> None:
    issue = QualityIssue("draft", "continuity", "Ada is 30, then 31", blocking=False)
    report = json.loads(QualityReport().render("herbs", (issue,), passing()))
    assert report["issues"] == [
        {"stage": "draft", "code": "continuity", "detail": "Ada is 30, then 31", "blocking": False}
    ]


def test_the_same_inputs_give_the_same_bytes_and_a_trailing_newline() -> None:
    first = QualityReport().render("herbs", (), passing())
    assert first == QualityReport().render("herbs", (), passing())
    assert first.endswith(b"}\n")
    assert list(json.loads(first)) == sorted(json.loads(first))


def test_the_spend_block_sets_what_was_spent_beside_what_was_expected() -> None:
    spend = SpendSummary(5_000_000, 1_500_000, 1_000_000, 1_500_000)
    report = json.loads(QualityReport().render("herbs", (), passing(), spend))
    assert report["spend"] == {
        "cap_micro_usd": 5_000_000,
        "spent_micro_usd": 1_500_000,
        "estimated_micro_usd": 1_000_000,
        "estimated_high_micro_usd": 1_500_000,
        "spent_over_estimated": 1.5,
    }


def test_with_no_estimate_the_spend_block_still_says_what_was_spent() -> None:
    report = json.loads(QualityReport().render("herbs", (), passing(), SpendSummary(10, 4)))
    assert report["spend"]["estimated_micro_usd"] is None
    assert (
        report["spend"]["spent_over_estimated"] is None and report["spend"]["spent_micro_usd"] == 4
    )


def test_without_a_summary_there_is_no_spend_block_so_old_reports_do_not_change() -> None:
    assert "spend" not in json.loads(QualityReport().render("herbs", (), passing()))
