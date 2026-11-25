# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""Drives a non-fiction run through every stage of its plan, in one process, and reports what happened.

The same driver runs two ways: against a scripted local server as a free rehearsal that proves the whole
chain works through the real runtime and HTTP adapters, and against a real model as a paid, capped test
(``tests/paid``). It composes the run machinery with in-memory adapters, so it needs no database, queue or
worker, and writes every artifact, and a report, to a folder for a person to read.
"""

import asyncio
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

from engineering_influence.infrastructure.export.directory_project_files_writer import (
    DirectoryProjectFilesWriter,
)
from engineering_influence.infrastructure.in_memory_artifact_store import InMemoryArtifactStore
from engineering_influence.infrastructure.in_memory_journal import InMemoryJournal
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.in_memory_run_repository import InMemoryRunRepository
from engineering_influence.interfaces.manuscript_builder_interface import ManuscriptBuilderInterface
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.models.advance_outcome import AdvanceOutcome
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_kind import BookKind
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget import Budget
from engineering_influence.models.run_status import RunStatus
from engineering_influence.runtime.stage_executor_runtime import StageExecutorRuntime
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.failure_classifier import FailureClassifier
from engineering_influence.services.nonfiction_recipes import NonfictionRecipes
from engineering_influence.services.novel_recipes import NovelRecipes

RUN_ID = "smoke-1"
DEFAULT_IDEA = "How to keep culinary herbs alive on a sunny windowsill"
DEFAULT_TARGET_WORDS = 1_200
REQUIRED = (
    "EI_SMOKE_PROFILE",
    "EI_MODEL_PROFILES",
    "EI_MODEL_CATALOG",
    "EI_SMOKE_BUDGET_MICRO_USD",
)
SYNTHETIC_AUTHOR = (
    'author = "Smoke Test Author"\npublisher = "Smoke Test Press"\nedition = "First Edition"\n'
    'author_bio = "A made-up author, used only to test the pipeline."\nyear = 2031\n'
)
MAX_ATTEMPTS = 3
STOPPED = frozenset({RunStatus.FAILED, RunStatus.PARKED_CAPACITY, RunStatus.CANCELLED})


@dataclass(frozen=True)
class LiveSettings:
    """What a paid smoke run needs, read from the environment, with a hard spending cap that has no default.

    The cap, the model profile and the profile and catalog files are required, so a run cannot start by accident or without a
    limit. The author's details are always a made-up author written to the scratch folder: a smoke test never
    uses a real person's profile. Nothing here reads a key; the model profile names the variable that holds it.
    """

    environment: dict[str, str]
    brief: BookBrief
    out: Path

    @classmethod
    def from_environment(cls, source: Mapping[str, str], scratch: Path) -> "LiveSettings":
        """The settings, or a ValueError saying which variable is missing or wrong."""
        missing = [name for name in REQUIRED if not source.get(name, "").strip()]
        if missing:
            raise ValueError(
                f"set {', '.join(missing)} (see docs/LIVE_SMOKE_TEST.md); the budget has no default on purpose"
            )
        cap = cls._whole("EI_SMOKE_BUDGET_MICRO_USD", source["EI_SMOKE_BUDGET_MICRO_USD"])
        words = cls._whole(
            "EI_SMOKE_TARGET_WORDS",
            source.get("EI_SMOKE_TARGET_WORDS") or str(DEFAULT_TARGET_WORDS),
        )
        author = scratch / "author.toml"
        author.parent.mkdir(parents=True, exist_ok=True)
        author.write_text(SYNTHETIC_AUTHOR, encoding="utf-8")
        named = source.get("EI_SMOKE_OUT", "").strip()
        return cls(
            environment={
                **source,
                "EI_STAGE_EXECUTOR": "model",
                "EI_STAGE_MODEL_PROFILE": source["EI_SMOKE_PROFILE"],
                "EI_AUTHOR_PROFILE": str(author),
            },
            brief=BookBrief(
                kind=BookKind.NONFICTION,
                idea=source.get("EI_SMOKE_IDEA") or DEFAULT_IDEA,
                budget_micro_usd=cap,
                target_words=words,
            ),
            out=Path(named) if named else scratch / "out",
        )

    @staticmethod
    def _whole(name: str, value: str) -> int:
        try:
            number = int(value)
        except ValueError:
            number = 0
        if number < 1:
            raise ValueError(f"{name} is a whole number above zero, not {value!r}")
        return number


@dataclass(frozen=True)
class StageRow:
    """One stage: how it ended, what it cost and how long it took."""

    stage: str
    outcome: str
    attempts: int
    spent_micro_usd: int
    seconds: float


@dataclass(frozen=True)
class SmokeReport:
    """What a run did, and every artifact it stored."""

    status: str
    stage: str
    cap_micro_usd: int
    spent_micro_usd: int
    rows: tuple[StageRow, ...]
    issues: tuple[str, ...]
    artifacts: Mapping[str, bytes] = field(repr=False)

    @property
    def completed(self) -> bool:
        return self.status == RunStatus.COMPLETED.value

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "stage": self.stage,
            "budget": {
                "cap_micro_usd": self.cap_micro_usd,
                "spent_micro_usd": self.spent_micro_usd,
                "spent_usd": round(self.spent_micro_usd / 1_000_000, 4),
            },
            "stages": [
                {
                    "stage": row.stage,
                    "outcome": row.outcome,
                    "attempts": row.attempts,
                    "spent_micro_usd": row.spent_micro_usd,
                    "seconds": row.seconds,
                }
                for row in self.rows
            ],
            "issues": list(self.issues),
            "artifacts": sorted(self.artifacts),
        }

    def write(self, folder: Path) -> None:
        """Write every artifact, and ``smoke-report.json``, to a new or empty folder."""
        files = dict(self.artifacts)
        files["smoke-report.json"] = (json.dumps(self.as_dict(), indent=2) + "\n").encode("utf-8")
        DirectoryProjectFilesWriter().write(folder, files)


class SmokeRun:
    """Runs the plan stage by stage, retrying a stage that says it will be retried, and stops at the first that does not advance."""

    def __init__(
        self,
        environment: Mapping[str, str],
        secrets: SecretProviderInterface,
        brief: BookBrief,
        today: date | None = None,
        builder: ManuscriptBuilderInterface | None = None,
    ) -> None:
        self._runtime = StageExecutorRuntime(
            environment, secrets, today or date.today(), builder=builder
        )
        self._brief = brief

    def run(self) -> SmokeReport:
        """Run every stage of the plan for the brief's kind of book, or as many as advance."""
        store, journal = InMemoryArtifactStore(), InMemoryJournal()
        runs = InMemoryRunRepository()
        executor = self._runtime.build(store, journal)
        try:
            service = AdvanceRun(runs, journal, executor, InMemoryQueue(), FailureClassifier())
            plan = (
                NovelRecipes() if self._brief.kind is BookKind.NOVEL else NonfictionRecipes()
            ).plan()
            cap = self._brief.budget_micro_usd
            runs.save(BookRun(RUN_ID, self._brief, plan, Budget(cap=cap)))
            rows: list[StageRow] = []
            for stage in plan.stages:
                row = self._stage(service, runs, stage)
                rows.append(row)
                if self._current(runs).status in STOPPED:
                    break
            final = self._current(runs)
            return SmokeReport(
                status=final.status.value,
                stage=final.stage,
                cap_micro_usd=cap,
                spent_micro_usd=final.budget.spent,
                rows=tuple(rows),
                issues=tuple(f"{issue.code}: {issue.detail}" for issue in final.issues),
                artifacts={name: store.get(RUN_ID, name) or b"" for name in store.names(RUN_ID)},
            )
        finally:
            self._runtime.close()

    def _stage(self, service: AdvanceRun, runs: InMemoryRunRepository, stage: str) -> StageRow:
        before = self._current(runs).budget.spent
        started = time.monotonic()
        attempt, outcome = 1, AdvanceOutcome.RETRYING
        while outcome is AdvanceOutcome.RETRYING and attempt <= MAX_ATTEMPTS:
            outcome = asyncio.run(service.advance(RUN_ID, stage, attempt))
            attempt += 1
        return StageRow(
            stage=stage,
            outcome=outcome.value,
            attempts=attempt - 1,
            spent_micro_usd=self._current(runs).budget.spent - before,
            seconds=round(time.monotonic() - started, 1),
        )

    @staticmethod
    def _current(runs: InMemoryRunRepository) -> BookRun:
        stored = runs.get(RUN_ID)
        assert stored is not None
        return stored
