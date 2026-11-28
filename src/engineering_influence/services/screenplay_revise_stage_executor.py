# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The revision stage of a screenplay: each drafted scene is revised once, and kept only if the revision is usable."""

import asyncio
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.spend_consent_needed_error import SpendConsentNeededError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.scene_reviser_interface import SceneReviserInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.scene_card import SceneCard
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.scene_card_list_interface import (
    SceneCardListInterface,
)
from engineering_influence.services.interfaces.screenplay_dialogue_source_check_interface import (
    ScreenplayDialogueSourceCheckInterface,
)
from engineering_influence.services.interfaces.screenplay_section_check_interface import (
    ScreenplaySectionCheckInterface,
)


class ScreenplayReviseStageExecutor(StageExecutorInterface):
    """Each drafted scene (`scenes/NNN.md`) is revised by one call and stored as `revised/NNN.md`.

    **A revision is kept only if it is usable.** It must pass the same section check as the draft and be within
    ``MIN_RATIO`` to ``MAX_RATIO`` of the draft's length in words; otherwise the drafted scene is stored unchanged, so
    the assembly always has a scene for every card. A scene already revised is kept, so a redelivered stage revises
    only what is missing.

    **The revision is optional, so a run that runs out of money keeps the drafts.** When a call would pass the cap,
    that scene and every later one keep their draft; nothing more is sent. The stage's report counts the scenes that
    kept their draft, whether rejected, unchanged, or left for want of money, and that count is read back from the
    stored files, so a redelivery reports the same.
    """

    STAGE: ClassVar[str] = "revise_scenes"
    MIN_RATIO: ClassVar[float] = 0.9
    MAX_RATIO: ClassVar[float] = 1.1

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        reviser: SceneReviserInterface,
        cards: SceneCardListInterface,
        checks: ScreenplaySectionCheckInterface,
        dialogue: ScreenplayDialogueSourceCheckInterface,
    ) -> None:
        """Remember the artifacts, reviser, scene cards, section checks and dialogue check the revisions use."""
        self._artifacts = artifacts
        self._reviser = reviser
        self._cards = cards
        self._checks = checks
        self._dialogue = dialogue

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Revise the scenes that are not yet revised, then report how many kept their draft."""
        cards = self._cards.parse(await self._required(run, "scene_cards.md"))
        out_of_money = False
        for card in cards:
            if await self._read(run, card.revised()) is not None:
                continue
            scene = await self._required(run, card.artifact())
            sources = await self._cited(run, card)
            if out_of_money:
                await self._put(run, card.revised(), scene)
                continue
            try:
                answer = await asyncio.to_thread(self._reviser.revise, run, card, scene)
            except SpendConsentNeededError:
                out_of_money = True
                await self._put(run, card.revised(), scene)
                continue
            usable = self._usable(scene, answer, sources)
            await self._put(run, card.revised(), answer if usable else scene)
        return await self._report(run, cards)

    async def _cited(self, run: BookRun, card: SceneCard) -> str:
        """The source files the card names, as the draft stage gives them to the scene's dialogue check."""
        blocks = [
            f"Source {number:03d}:\n{await self._required(run, f'source/{number:03d}.md')}"
            for number in card.sources
        ]
        return "\n\n".join(blocks)

    def _usable(self, draft: str, answer: str, sources: str) -> bool:
        if self._checks.problems(answer) or self._dialogue.problems(answer, sources):
            return False
        before, after = len(draft.split()), len(answer.split())
        return self.MIN_RATIO * before <= after <= self.MAX_RATIO * before

    async def _report(self, run: BookRun, cards: tuple[SceneCard, ...]) -> StageReport:
        kept = 0
        for card in cards:
            revised = await self._required(run, card.revised())
            draft = await self._required(run, card.artifact())
            if revised == draft:
                kept += 1
        if kept == 0:
            return StageReport()
        issue = QualityIssue(
            run.stage,
            "revision-kept-draft",
            f"{kept} of {len(cards)} scenes kept their drafted text: the revision was rejected, unchanged, "
            "or left for want of money",
            blocking=False,
        )
        return StageReport((issue,))

    async def _required(self, run: BookRun, name: str) -> str:
        data = await self._read(run, name)
        if data is None:
            raise ApplicationError(
                code="STAGE_INPUT_MISSING",
                message=f"stage {run.stage!r} needs {name}, which this run has not stored",
                http_status=409,
            )
        return data

    async def _read(self, run: BookRun, name: str) -> str | None:
        data = await asyncio.to_thread(self._artifacts.get, run.run_id, name)
        return None if data is None else data.decode("utf-8")

    async def _put(self, run: BookRun, name: str, text: str) -> None:
        await asyncio.to_thread(self._artifacts.put, run.run_id, name, text.encode("utf-8"))
