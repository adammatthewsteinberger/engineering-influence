# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The drafting stage of a screenplay: each scene in prompt 09's order, checked, kept, and assembled into one script."""

import asyncio
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.scene_drafter_interface import SceneDrafterInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.scene_card import SceneCard
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.scene_card_list_interface import (
    SceneCardListInterface,
)
from engineering_influence.services.interfaces.screenplay_assembler_interface import (
    ScreenplayAssemblerInterface,
)
from engineering_influence.services.interfaces.screenplay_section_check_interface import (
    ScreenplaySectionCheckInterface,
)
from engineering_influence.services.screenplay_drafting_order import ScreenplayDraftingOrder


class ScreenplayDraftStageExecutor(StageExecutorInterface):
    """A scene that fails its check is drafted once more; if the second draft fails too, the stage stops and names the
    problems. A scene already stored is kept, so a redelivered stage drafts only what is missing. Once every scene is
    stored, the script is assembled in card order and stored as `screenplay.fountain`."""

    SCRIPT: ClassVar[str] = "screenplay.fountain"
    DRAFT_ATTEMPTS: ClassVar[int] = 2
    MAX_PROBLEMS_SHOWN: ClassVar[int] = 5

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        drafter: SceneDrafterInterface,
        cards: SceneCardListInterface,
        checks: ScreenplaySectionCheckInterface,
        assembler: ScreenplayAssemblerInterface,
        title_page: tuple[tuple[str, str], ...],
        shareable: frozenset[int] = frozenset(),
    ) -> None:
        self._artifacts = artifacts
        self._drafter = drafter
        self._cards = cards
        self._checks = checks
        self._assembler = assembler
        self._title_page = title_page
        self._shareable = shareable

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Draft the missing scenes in drafting order, then assemble the script."""
        cards = self._cards.parse(await self._required(run, "scene_cards.md"))
        anchors = await self._required(run, "anchors.md")
        beats = await self._required(run, "beats.md")
        by_number = {card.number: card for card in cards}
        order = ScreenplayDraftingOrder().order(
            tuple((card.number, card.beat) for card in cards), self._shareable
        )
        stored = set(await asyncio.to_thread(self._artifacts.names, run.run_id))
        for number in order:
            card = by_number[number]
            if card.artifact() in stored:
                continue
            scene = await self._scene(run, card, anchors, beats)
            await self._put(run, card.artifact(), scene)
        if self.SCRIPT not in stored:
            scenes = tuple([await self._required(run, card.artifact()) for card in cards])
            script = self._assembler.assemble(self._title_page, scenes)
            await self._put(run, self.SCRIPT, script)
        return StageReport()

    async def _scene(self, run: BookRun, card: SceneCard, anchors: str, beats: str) -> str:
        problems: tuple[str, ...] = ()
        for number in range(1, self.DRAFT_ATTEMPTS + 1):
            scene = await asyncio.to_thread(self._drafter.draft, run, card, anchors, beats, number)
            problems = self._checks.problems(scene)
            if not problems:
                return scene
        shown = "; ".join(problems[: self.MAX_PROBLEMS_SHOWN])
        raise ApplicationError(
            code="STAGE_OUTPUT_INVALID",
            message=f"S{card.number:02d}: {shown}",
            http_status=422,
        )

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
