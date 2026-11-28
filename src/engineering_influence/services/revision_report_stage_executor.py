# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The report stage of a screenplay: the revision log and the source mapping, written from what the run stored."""

import asyncio
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.scene_revision import SceneRevision
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.revision_report_writer_interface import (
    RevisionReportWriterInterface,
)
from engineering_influence.services.interfaces.scene_card_list_interface import (
    SceneCardListInterface,
)
from engineering_influence.services.interfaces.shooting_lock_codec_interface import (
    ShootingLockCodecInterface,
)


class RevisionReportStageExecutor(StageExecutorInterface):
    """No model call. A scene's revision was not used when the stored revision is the draft unchanged, which is what
    the revision stage stores when it rejects a revision or runs out of money. The stage writes `revision_log.md` and
    `source_mapping.md`, both in the locked script's order, and stops when the lock and the cards disagree.
    """

    STAGE: ClassVar[str] = "log_revisions"
    CARDS: ClassVar[str] = "scene_cards.md"
    LOCK: ClassVar[str] = "shooting_lock.json"
    LOG: ClassVar[str] = "revision_log.md"
    MAPPING: ClassVar[str] = "source_mapping.md"

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        cards: SceneCardListInterface,
        codec: ShootingLockCodecInterface,
        writer: RevisionReportWriterInterface,
    ) -> None:
        """Remember the artifacts, scene cards, shooting lock codec and report writer."""
        self._artifacts = artifacts
        self._cards = cards
        self._codec = codec
        self._writer = writer

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Read the cards, the lock and each scene's draft and revision, then store both reports."""
        cards = self._cards.parse(await self._required(run, self.CARDS))
        lock = self._codec.decode(await self._required(run, self.LOCK))
        scenes: list[SceneRevision] = []
        for card in cards:
            draft = await self._required(run, card.artifact())
            revised = await self._required(run, card.revised())
            scenes.append(
                SceneRevision(card, len(draft.split()), len(revised.split()), revised == draft)
            )
        try:
            log = self._writer.revision_log(lock, tuple(scenes))
            mapping = self._writer.source_mapping(lock, tuple(scenes))
        except ValueError as error:
            raise ApplicationError(
                code="STAGE_OUTPUT_INVALID", message=str(error), http_status=422
            ) from error
        await self._put(run, self.LOG, log)
        await self._put(run, self.MAPPING, mapping)
        return StageReport()

    async def _required(self, run: BookRun, name: str) -> str:
        data = await asyncio.to_thread(self._artifacts.get, run.run_id, name)
        if data is None:
            raise ApplicationError(
                code="STAGE_INPUT_MISSING",
                message=f"stage {run.stage!r} needs {name}, which this run has not stored",
                http_status=409,
            )
        return data.decode("utf-8")

    async def _put(self, run: BookRun, name: str, text: str) -> None:
        await asyncio.to_thread(self._artifacts.put, run.run_id, name, text.encode("utf-8"))
