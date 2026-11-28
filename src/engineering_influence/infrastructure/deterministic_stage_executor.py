# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A placeholder stage executor that needs no model and no network."""

import asyncio
import hashlib

from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.journal_interface import JournalInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.journal_entry import JournalEntry
from engineering_influence.models.journal_key import JournalKey
from engineering_influence.models.stage_report import StageReport


class DeterministicStageExecutor(StageExecutorInterface):
    """Writes ``<stage>.md`` from the brief's idea, through the journal, at no cost.

    This is the default so a ``run.advance`` job can run offline and reproducibly, the way
    ``DeterministicRunner`` does for pipelines. It goes through the same journal and write-once
    store a model-backed executor will use, so a repeated stage replays the first answer.
    """

    def __init__(self, artifacts: ArtifactStoreInterface, journal: JournalInterface) -> None:
        """Remember the artifact store and the journal the stage writes through."""
        self._artifacts = artifacts
        self._journal = journal

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Record a zero-cost journal entry and store the stage's artifact."""
        context = hashlib.sha256(f"{run.stage}\x1f{run.brief.idea}".encode()).hexdigest()
        entry = JournalEntry(
            run_id=run.run_id,
            stage=run.stage,
            attempt=attempt,
            key=JournalKey("deterministic", "none", "v0", context),
            response=f"{run.stage}: draft for {run.brief.idea}",
            cost_micro_usd=0,
        )
        recorded = await asyncio.to_thread(self._journal.record, entry)
        await asyncio.to_thread(
            self._artifacts.put, run.run_id, f"{run.stage}.md", recorded.response.encode()
        )
        return StageReport()
