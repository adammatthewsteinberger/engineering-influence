# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The locking stage of a screenplay: the script's scenes get their numbers, and the numbers are kept from then on."""

import asyncio
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.shooting_lock import ShootingLock
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.fountain_parser_interface import (
    FountainParserInterface,
)
from engineering_influence.services.interfaces.scene_card_list_interface import (
    SceneCardListInterface,
)
from engineering_influence.services.interfaces.shooting_lock_codec_interface import (
    ShootingLockCodecInterface,
)
from engineering_influence.services.interfaces.shooting_lock_planner_interface import (
    ShootingLockPlannerInterface,
)
from engineering_influence.services.interfaces.shooting_revision_marks_interface import (
    ShootingRevisionMarksInterface,
)
from engineering_influence.services.interfaces.shooting_script_renderer_interface import (
    ShootingScriptRendererInterface,
)
from engineering_influence.services.shooting_revision_marks import ShootingRevisionMarks


class LockShootingScriptStageExecutor(StageExecutorInterface):
    """No model call. Each scene card is one scene of the script, in card order, and the stage stops when the two
    disagree, naming both counts.

    The numbers are planned from the previous lock, if the run was given one as ``previous_shooting_lock.json``, and
    from nothing otherwise. The plan is deterministic, so a stage that runs again in the same run writes the same lock.
    The lock is stored as ``shooting_lock.json``, the numbered script as ``shooting_script.fountain``. Stored artifacts
    are never rewritten, which is why the previous lock has its own name.
    """

    STAGE: ClassVar[str] = "lock_script"
    SCRIPT: ClassVar[str] = "screenplay.fountain"
    CARDS: ClassVar[str] = "scene_cards.md"
    PREVIOUS: ClassVar[str] = "previous_shooting_lock.json"
    LOCK: ClassVar[str] = "shooting_lock.json"
    SHOOTING_SCRIPT: ClassVar[str] = "shooting_script.fountain"

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        cards: SceneCardListInterface,
        parser: FountainParserInterface,
        planner: ShootingLockPlannerInterface,
        codec: ShootingLockCodecInterface,
        renderer: ShootingScriptRendererInterface,
        marks: ShootingRevisionMarksInterface,
    ) -> None:
        self._artifacts = artifacts
        self._cards = cards
        self._parser = parser
        self._planner = planner
        self._codec = codec
        self._renderer = renderer
        self._marks = marks

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Plan the lock for the cards, then store the lock and the numbered script."""
        numbers = tuple(
            card.number for card in self._cards.parse(await self._required(run, self.CARDS))
        )
        script = await self._required(run, self.SCRIPT)
        scenes = len(self._parser.scene_chunks(script)[1])
        if scenes != len(numbers):
            raise ApplicationError(
                code="STAGE_OUTPUT_INVALID",
                message=f"the script has {scenes} scenes but the scene cards name {len(numbers)}; "
                "each card is one scene",
                http_status=422,
            )
        lock = self._plan(await self._previous(run), numbers)
        await self._put(run, self.LOCK, self._codec.encode(lock))
        rendered = self._renderer.render(script, numbers, lock)
        await self._put(run, self.SHOOTING_SCRIPT, rendered)
        baseline = await asyncio.to_thread(
            self._artifacts.get, run.run_id, ShootingRevisionMarks.BASELINE
        )
        if baseline is not None:
            pages = self._revision_pages(
                await self._required(run, ShootingRevisionMarks.REVISION),
                baseline.decode("utf-8"),
                rendered,
                await self._optional(run, ShootingRevisionMarks.REVISION_DATE),
            )
            await self._put(run, ShootingRevisionMarks.PAGES, pages)
        return StageReport()

    def _revision_pages(
        self, revision: str, baseline: str, rendered: str, revision_date: str | None
    ) -> str:
        """The rendered script with its changed scenes marked as this revision's colour."""
        try:
            return self._marks.mark(baseline, rendered, int(revision), revision_date)
        except ValueError as error:
            raise ApplicationError(
                code="STAGE_OUTPUT_INVALID", message=str(error), http_status=422
            ) from error

    def _plan(self, previous: ShootingLock, numbers: tuple[int, ...]) -> ShootingLock:
        try:
            return self._planner.plan(previous, numbers)
        except ValueError as error:
            raise ApplicationError(
                code="STAGE_OUTPUT_INVALID", message=str(error), http_status=422
            ) from error

    async def _previous(self, run: BookRun) -> ShootingLock:
        data = await asyncio.to_thread(self._artifacts.get, run.run_id, self.PREVIOUS)
        return ShootingLock() if data is None else self._codec.decode(data.decode("utf-8"))

    async def _optional(self, run: BookRun, name: str) -> str | None:
        data = await asyncio.to_thread(self._artifacts.get, run.run_id, name)
        return None if data is None else data.decode("utf-8")

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
