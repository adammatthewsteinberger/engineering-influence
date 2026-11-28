# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The drafting stage of a screenplay: each scene in prompt 09's order, checked and kept. Assembly is a later stage."""

import asyncio
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.scene_drafter_interface import SceneDrafterInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.scene_card import SceneCard
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.answer_screen_interface import AnswerScreenInterface
from engineering_influence.services.interfaces.scene_card_list_interface import (
    SceneCardListInterface,
)
from engineering_influence.services.interfaces.screenplay_bible_context_interface import (
    ScreenplayBibleContextInterface,
)
from engineering_influence.services.interfaces.screenplay_dialogue_source_check_interface import (
    ScreenplayDialogueSourceCheckInterface,
)
from engineering_influence.services.interfaces.screenplay_section_check_interface import (
    ScreenplaySectionCheckInterface,
)
from engineering_influence.services.screenplay_drafting_order import ScreenplayDraftingOrder


class ScreenplayDraftStageExecutor(StageExecutorInterface):
    """A scene that fails its check is drafted once more; if the second draft fails too, the stage stops and names the
    problems. A scene already stored is kept, so a redelivered stage drafts only what is missing."""

    DRAFT_ATTEMPTS: ClassVar[int] = 2
    MAX_PROBLEMS_SHOWN: ClassVar[int] = 5

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        drafter: SceneDrafterInterface,
        cards: SceneCardListInterface,
        checks: ScreenplaySectionCheckInterface,
        dialogue: ScreenplayDialogueSourceCheckInterface,
        screen: AnswerScreenInterface,
        shareable: frozenset[int] = frozenset(),
        bible: ScreenplayBibleContextInterface | None = None,
    ) -> None:
        """Remember the artifacts, drafter, scene cards, section checks and dialogue check the drafts use."""
        self._artifacts = artifacts
        self._drafter = drafter
        self._cards = cards
        self._checks = checks
        self._dialogue = dialogue
        self._screen = screen
        self._shareable = shareable
        self._bible = bible

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Draft the missing scenes in drafting order."""
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
            scene = await self._scene(run, card, anchors, beats, await self._cited(run, card))
            await self._put(run, card.artifact(), scene)
        return StageReport()

    async def _cited(self, run: BookRun, card: SceneCard) -> str:
        """The source files the card names, each under its number, and the bible cards the scene names."""
        blocks = [
            f"Source {number:03d}:\n{await self._required(run, f'source/{number:03d}.md')}"
            for number in card.sources
        ]
        cited = "\n\n".join(blocks)
        if self._bible is None:
            return cited
        named = await asyncio.to_thread(
            self._bible.for_scene, run.run_id, f"{card.beat}\n{card.body}\n{cited}"
        )
        return cited if not named else f"{cited}\n\n{named}"

    async def _scene(
        self, run: BookRun, card: SceneCard, anchors: str, beats: str, sources: str
    ) -> str:
        findings = ""
        problems: tuple[str, ...] = ()
        for number in range(1, self.DRAFT_ATTEMPTS + 1):
            scene = await asyncio.to_thread(
                self._drafter.draft, run, card, anchors, beats, sources, number, findings
            )
            problems = self._problems(scene, sources)
            if not problems:
                return scene
            # The second draft is told why the first one failed, so it corrects those problems rather than guessing.
            findings = "; ".join(problems[: self.MAX_PROBLEMS_SHOWN])
        shown = "; ".join(problems[: self.MAX_PROBLEMS_SHOWN])
        raise ApplicationError(
            code="STAGE_OUTPUT_INVALID",
            message=f"S{card.number:02d}: {shown}",
            http_status=422,
        )

    def _problems(self, scene: str, sources: str) -> tuple[str, ...]:
        """Everything wrong with a draft: a refusal in its action, a broken format, or dialogue that copies a source."""
        refusal = (
            ("the draft opens with a refusal, not a scene",) if self._screen.refused(scene) else ()
        )
        return refusal + self._checks.problems(scene) + self._dialogue.problems(scene, sources)

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
