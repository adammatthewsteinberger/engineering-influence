"""The build stage builds the assembled book, stores the files and the evidence, and stops the run on a book that fails."""

import asyncio
import json
from collections.abc import Mapping
from dataclasses import replace

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.interfaces.manuscript_builder_interface import (
    ManuscriptBuilderInterface,
)
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.cost_estimate import CostEstimate
from engineering_influence.models.manuscript_build import ManuscriptBuild
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.services.build_stage_executor import BuildStageExecutor
from engineering_influence.services.interfaces.cost_estimator_interface import (
    CostEstimatorInterface,
)
from engineering_influence.services.manuscript_project import ManuscriptProject
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.quality_report import QualityReport

RUN = "run-1"
PASS = ManuscriptBuild(
    True,
    "pass",
    (),
    ("price: no price",),
    (("pdf", "pass"), ("epub", "pass")),
    (("publication-report.json", b"{}"), ("pdf.log", b"ok")),
    (("listing.md", b"# Listing\n"), ("herbs.pdf", b"%PDF")),
)
FAIL = ManuscriptBuild(
    False,
    "fail",
    ("step pdf failed: no font", "missing artifact: output/herbs.epub"),
    (),
    (("pdf", "fail"),),
    (("publication-report.json", b"{}"),),
    (),
)


class Builder(ManuscriptBuilderInterface):
    def __init__(self, result: ManuscriptBuild) -> None:
        self.result = result
        self.seen: list[tuple[list[str], str]] = []

    def build(self, files: Mapping[str, bytes], slug: str) -> ManuscriptBuild:
        self.seen.append((sorted(files), slug))
        return self.result


def world(result: ManuscriptBuild) -> tuple[BuildStageExecutor, InMemoryArtifactStore, Builder]:
    store = InMemoryArtifactStore()
    store.put(RUN, "manuscript/books/herbs.toml", b"title = 'Herbs'")
    store.put(RUN, "manuscript/src/chapter_01.md", b"# One")
    builder = Builder(result)
    executor = BuildStageExecutor(store, builder, ManuscriptProject(store), QualityReport())
    return executor, store, builder


def run() -> BookRun:
    brief = BookBrief(BookKind.NONFICTION, "Herbs", 1_000)
    return BookRun(RUN, brief, NonfictionRecipes().plan(), Budget(cap=1_000), stage="build")


def test_it_is_the_build_stage() -> None:
    assert BuildStageExecutor.STAGE == "build"
    assert NonfictionRecipes().plan().stages[-1] == BuildStageExecutor.STAGE


def test_the_builder_is_given_the_assembled_project() -> None:
    executor, _, builder = world(PASS)
    asyncio.run(executor.execute(run(), 1))
    assert builder.seen == [(["books/herbs.toml", "src/chapter_01.md"], "herbs")]


def test_a_passing_build_stores_the_bundle_the_evidence_and_the_reports() -> None:
    executor, store, _ = world(PASS)
    asyncio.run(executor.execute(run(), 1))
    assert store.get(RUN, "book/listing.md") == b"# Listing\n"
    assert store.get(RUN, "book/herbs.pdf") == b"%PDF"
    assert store.get(RUN, "build/publication-report.json") == b"{}"
    assert store.get(RUN, "build/pdf.log") == b"ok"
    report = json.loads(store.get(RUN, "quality-report.json") or b"")
    assert report["status"] == "pass" and len(report["files"]) == 2
    summary = (store.get(RUN, "build.md") or b"").decode()
    assert "Status: pass" in summary and "- pdf: pass" in summary and "- price: no price" in summary


def test_a_failing_build_stores_everything_before_it_stops_the_run() -> None:
    executor, store, _ = world(FAIL)
    with pytest.raises(ApplicationError) as stopped:
        asyncio.run(executor.execute(run(), 1))
    assert stopped.value.code == "BUILD_FAILED" and stopped.value.http_status == 422
    assert "step pdf failed: no font; missing artifact: output/herbs.epub" in stopped.value.message
    assert "'herbs'" in stopped.value.message
    assert store.get(RUN, "build/publication-report.json") == b"{}"
    assert json.loads(store.get(RUN, "quality-report.json") or b"")["status"] == "fail"
    assert "Status: fail" in (store.get(RUN, "build.md") or b"").decode()
    assert not [name for name in store.names(RUN) if name.startswith("book/")]


def test_the_quality_report_carries_the_issues_the_run_recorded() -> None:
    executor, store, _ = world(PASS)
    issue = QualityIssue("draft", "continuity", "Ada is 30, then 31", blocking=False)
    recorded = run().with_issue(issue)
    asyncio.run(executor.execute(recorded, 1))
    report = json.loads(store.get(RUN, "quality-report.json") or b"")
    assert [item["code"] for item in report["issues"]] == ["continuity"]


def test_a_run_without_an_assembled_book_is_refused_before_anything_is_built() -> None:
    store = InMemoryArtifactStore()
    builder = Builder(PASS)
    executor = BuildStageExecutor(store, builder, ManuscriptProject(store), QualityReport())
    with pytest.raises(ApplicationError) as refused:
        asyncio.run(executor.execute(run(), 1))
    assert refused.value.code == "STAGE_INPUT_MISSING" and builder.seen == []


class Estimating(CostEstimatorInterface):
    def __init__(self) -> None:
        self.briefs: list[BookBrief] = []

    def estimate(self, brief: BookBrief) -> CostEstimate:
        self.briefs.append(brief)
        return CostEstimate((("draft", 600, True), ("copy_edit", 200, False)))


def test_the_report_records_the_estimate_made_from_the_brief_beside_the_real_spend() -> None:
    store = InMemoryArtifactStore()
    store.put(RUN, "manuscript/books/herbs.toml", b"title = 'Herbs'")
    store.put(RUN, "manuscript/src/chapter_01.md", b"# One")
    estimator = Estimating()
    executor = BuildStageExecutor(
        store, Builder(PASS), ManuscriptProject(store), QualityReport(), estimator
    )
    spent = replace(run(), budget=Budget(cap=1_000, spent=400))
    asyncio.run(executor.execute(spent, 1))
    report = json.loads(store.get(RUN, "quality-report.json") or b"")
    assert report["spend"] == {
        "cap_micro_usd": 1_000,
        "spent_micro_usd": 400,
        "estimated_micro_usd": 800,
        "estimated_high_micro_usd": 1_200,
        "spent_over_estimated": 0.5,
    }
    assert estimator.briefs == [spent.brief]


def test_without_an_estimator_the_report_still_records_the_spend() -> None:
    executor, store, _ = world(PASS)
    asyncio.run(executor.execute(replace(run(), budget=Budget(cap=1_000, spent=400)), 1))
    spend = json.loads(store.get(RUN, "quality-report.json") or b"")["spend"]
    assert (spend["cap_micro_usd"], spend["spent_micro_usd"], spend["estimated_micro_usd"]) == (
        1_000,
        400,
        None,
    )
