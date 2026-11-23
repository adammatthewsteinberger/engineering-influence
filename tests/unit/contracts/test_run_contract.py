"""The run summary contract: what the API and the CLI report about a book run."""

import json

import pytest
from pydantic import ValidationError

from engineering_influence.contracts.run.v1.run_summary_v1 import RunSummaryV1
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.run_status import RunStatus
from engineering_influence.models.stage_plan import StagePlan


def a_run() -> BookRun:
    brief = BookBrief(
        kind=BookKind.NOVEL, idea="a heist in a lighthouse " * 50, budget_micro_usd=5_000_000
    )
    plan = StagePlan(kind=BookKind.NOVEL, stages=("brief", "outline", "draft"))
    budget = Budget(cap=5_000_000, spent=1_200_000).reserve(300_000)
    return BookRun(
        "run-1",
        brief,
        plan,
        budget,
        stage="outline",
        status=RunStatus.PARKED_CAPACITY,
        issues=(QualityIssue("brief", "thin", "short idea", blocking=False),),
    )


def test_a_summary_describes_the_run_and_its_artifacts() -> None:
    summary = RunSummaryV1.from_run(a_run(), ["brief.md", "outline.md"])
    assert (summary.schema_version, summary.run_id, summary.kind) == (1, "run-1", BookKind.NOVEL)
    assert (summary.status, summary.stage) == (RunStatus.PARKED_CAPACITY, "outline")
    assert summary.stages == ("brief", "outline", "draft")
    assert summary.artifacts == ("brief.md", "outline.md")


def test_a_summary_reports_the_budget_in_micro_dollars() -> None:
    budget = RunSummaryV1.from_run(a_run(), []).budget
    assert (
        budget.cap_micro_usd,
        budget.spent_micro_usd,
        budget.reserved_micro_usd,
        budget.remaining_micro_usd,
    ) == (5_000_000, 1_200_000, 300_000, 3_500_000)


def test_a_summary_lists_the_issues() -> None:
    [issue] = RunSummaryV1.from_run(a_run(), []).issues
    assert (issue.stage, issue.code, issue.detail, issue.blocking) == (
        "brief",
        "thin",
        "short idea",
        False,
    )


def test_a_summary_leaves_the_idea_out() -> None:
    text = RunSummaryV1.from_run(a_run(), []).model_dump_json()
    assert "lighthouse" not in text


def test_a_summary_serialises_to_plain_json() -> None:
    document = RunSummaryV1.from_run(a_run(), ["a.md"]).model_dump(mode="json")
    assert json.loads(json.dumps(document)) == document
    assert document["kind"] == "novel"
    assert document["status"] == "parked_capacity"
    assert sorted(document) == [
        "artifacts",
        "budget",
        "consent_requested_micro_usd",
        "issues",
        "kind",
        "run_id",
        "schema_version",
        "stage",
        "stages",
        "status",
    ]
    assert sorted(document["budget"]) == [
        "cap_micro_usd",
        "remaining_micro_usd",
        "reserved_micro_usd",
        "spent_micro_usd",
    ]


def test_a_summary_cannot_be_changed_after_it_is_built() -> None:
    summary = RunSummaryV1.from_run(a_run(), [])
    with pytest.raises(ValidationError, match="frozen"):
        summary.stage = "draft"  # type: ignore[misc]


def test_a_summary_of_another_version_is_refused() -> None:
    document = RunSummaryV1.from_run(a_run(), []).model_dump(mode="json")
    with pytest.raises(ValidationError):
        RunSummaryV1.model_validate({**document, "schema_version": 2})


def test_a_summary_says_how_much_a_run_waiting_for_consent_asks_for() -> None:
    from engineering_influence.models.spend_request import SpendRequest

    waiting = a_run().await_consent(SpendRequest(700, "brief"))
    assert RunSummaryV1.from_run(waiting, []).consent_requested_micro_usd == 700
    assert RunSummaryV1.from_run(a_run(), []).consent_requested_micro_usd is None
