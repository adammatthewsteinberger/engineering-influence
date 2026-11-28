# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Wires one run of a book to stores in a folder and the real stage executors, with no database server or queue."""

from collections.abc import Callable, Mapping
from datetime import date
from pathlib import Path

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.export.directory_project_files_writer import (
    DirectoryProjectFilesWriter,
)
from engineering_influence.infrastructure.in_memory_queue import InMemoryQueue
from engineering_influence.infrastructure.schema_migrator import SchemaMigrator
from engineering_influence.interfaces.local_book_creator_interface import (
    LocalBookCreatorInterface,
)
from engineering_influence.interfaces.manuscript_builder_interface import (
    ManuscriptBuilderInterface,
)
from engineering_influence.interfaces.secret_provider_interface import SecretProviderInterface
from engineering_influence.models.bible_card import BibleCard
from engineering_influence.models.book_brief import BookBrief
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.budget_plan import BudgetPlan
from engineering_influence.models.export_summary import ExportSummary
from engineering_influence.models.source_entry import SourceEntry
from engineering_influence.repositories.sqlmodel_artifact_store import SqlModelArtifactStore
from engineering_influence.repositories.sqlmodel_journal import SqlModelJournal
from engineering_influence.repositories.sqlmodel_run_repository import SqlModelRunRepository
from engineering_influence.runtime.stage_executor_runtime import StageExecutorRuntime
from engineering_influence.services.advance_run import AdvanceRun
from engineering_influence.services.budget_planner import BudgetPlanner
from engineering_influence.services.create_run import CreateRun
from engineering_influence.services.export_run import ExportRun
from engineering_influence.services.failure_classifier import FailureClassifier
from engineering_influence.services.local_book_run import LocalBookRun
from engineering_influence.services.read_run import ReadRun
from engineering_influence.services.resolve_spend_consent import ResolveSpendConsent
from engineering_influence.services.resume_run import ResumeRun


class LocalBookRuntime(LocalBookCreatorInterface):
    """The same executors a worker runs, over a SQLite file in ``state_dir`` instead of a database server.

    The run, its journal of paid model calls and every artifact it stored are written to ``state_dir/state.db``
    as the run goes, so a process that dies loses nothing that was paid for: starting again with the same folder
    continues the run, and a model call already journaled is replayed, not paid for twice. The queue is in memory
    because this process is the only worker. ``environment`` is read as a worker reads its environment
    (``EI_STAGE_EXECUTOR``, the model profile, ``EI_AUTHOR_PROFILE``, ``EI_BUILD_STRICT_RELEASE``), so a book is
    made with exactly the settings a run on the stack would use.
    """

    DATABASE = "state.db"

    def __init__(
        self,
        state_dir: Path,
        environment: Mapping[str, str],
        secrets: SecretProviderInterface,
        today: date | None = None,
        builder: ManuscriptBuilderInterface | None = None,
    ) -> None:
        """Remember the state folder, environment, secrets, date and optional builder the local runs use."""
        self._stages = StageExecutorRuntime(
            environment, secrets, today or date.today(), builder=builder
        )
        self._check_inputs()
        state_dir.mkdir(parents=True, exist_ok=True)
        url = f"sqlite:///{(state_dir / self.DATABASE).resolve()}"
        SchemaMigrator().upgrade(url)
        runs = SqlModelRunRepository(url)
        self._runs = runs
        journal = SqlModelJournal(url)
        artifacts = SqlModelArtifactStore(url)
        self._stores = (runs, journal, artifacts)
        queue = InMemoryQueue()
        executor = self._stages.build(artifacts, journal)
        self._book = LocalBookRun(
            CreateRun(runs, queue, artifacts=artifacts),
            AdvanceRun(runs, journal, executor, queue, FailureClassifier()),
            ResumeRun(runs, queue),
            ResolveSpendConsent(runs, queue),
            runs,
        )
        self._export = ExportRun(ReadRun(runs, artifacts), DirectoryProjectFilesWriter())

    def _check_inputs(self) -> None:
        """Refuse, before anything is made or paid for, a book that could not be built at the end.

        The author's details are needed to typeset a book, and a strict release also needs the author's pricing.
        A run does not invent either, so finding them missing after every stage had been paid for would be the
        worst moment to learn it.
        """
        profile = self._stages.author_profile()
        if profile is None:
            raise ApplicationError(
                code="AUTHOR_PROFILE_REQUIRED",
                message="a book needs the author's details to be typeset: name an author profile "
                "(--profile FILE, or EI_AUTHOR_PROFILE)",
                http_status=422,
            )
        if self._stages.strict_release() and profile.pricing is None:
            raise ApplicationError(
                code="PRICING_REQUIRED",
                message="a strict release needs the author's pricing: add a [pricing] table "
                "(verified_on, source_url, ebook, paperback) to the author profile",
                http_status=422,
            )

    def plan(self, brief: BookBrief) -> BudgetPlan | None:
        """The brief's cap set against what the book is expected to cost, or None when no model is priced."""
        estimator = self._stages.estimator()
        return None if estimator is None else BudgetPlanner(estimator).plan(brief)

    def start(
        self,
        brief: BookBrief,
        progress: Callable[[str], None],
        sources: tuple[SourceEntry, ...] = (),
        previous_lock: str | None = None,
        stop_after: str | None = None,
        mode: str = "book",
        bible: tuple[BibleCard, ...] = (),
        title: str | None = None,
        previous_script: str | None = None,
        revision: int = 1,
        revision_date: str | None = None,
    ) -> BookRun:
        """Run the brief's plan, with its source files, until the run finishes or stops."""
        return self._book.start(
            brief,
            progress,
            sources,
            previous_lock,
            stop_after,
            mode,
            bible=bible,
            title=title,
            previous_script=previous_script,
            revision=revision,
            revision_date=revision_date,
        )

    def resume(self, approve_spend: bool, progress: Callable[[str], None]) -> BookRun:
        """Continue the run this folder holds."""
        return self._book.resume(approve_spend, progress)

    def export(self, directory: Path) -> ExportSummary:
        """Write what the run produced to a new or empty folder."""
        return self._export.export(self._runs.run_ids()[0], directory)

    def close(self) -> None:
        """Close the stage executors' connections and release the state file."""
        self._stages.close()
        for store in self._stores:
            store.close()
