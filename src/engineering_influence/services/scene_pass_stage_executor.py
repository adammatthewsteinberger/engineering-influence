# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A revision pass over every scene: one call per scene, kept only when the answer is usable, otherwise carried forward."""

import asyncio
from collections.abc import Callable
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.spend_consent_needed_error import SpendConsentNeededError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.scene_reviser_interface import SceneReviserInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.scene_card import SceneCard
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.scene_card_list_interface import (
    SceneCardListInterface,
)
from engineering_influence.services.interfaces.screenplay_section_check_interface import (
    ScreenplaySectionCheckInterface,
)


class ScenePassStageExecutor(StageExecutorInterface):
    """Each scene is read from `input_name` and the pass's answer stored under `output_name`. A pass that a scene's answer
    cannot improve on (rejected by the section check, or far from the scene's length) stores the scene unchanged, so every
    later stage always finds every scene. When the money runs out, that scene and the rest carry forward unchanged.
    """

    MIN_RATIO: ClassVar[float] = 0.9
    MAX_RATIO: ClassVar[float] = 1.1

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        stage: str,
        passer: SceneReviserInterface,
        cards: SceneCardListInterface,
        checks: ScreenplaySectionCheckInterface,
        input_name: Callable[[SceneCard], str],
        output_name: Callable[[SceneCard], str],
    ) -> None:
        """Remember the artifacts, the stage name, the scene reviser, the scene cards and the section checks."""
        self._artifacts = artifacts
        self._stage = stage
        self._passer = passer
        self._cards = cards
        self._checks = checks
        self._input = input_name
        self._output = output_name

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Pass each scene that has no output yet."""
        cards = self._cards.parse(await self._required(run, "scene_cards.md"))
        out_of_money = False
        for card in cards:
            if await self._read(run, self._output(card)) is not None:
                continue
            scene = await self._required(run, self._input(card))
            if out_of_money:
                await self._put(run, self._output(card), scene)
                continue
            try:
                answer = await asyncio.to_thread(self._passer.revise, run, card, scene)
            except SpendConsentNeededError:
                out_of_money = True
                await self._put(run, self._output(card), scene)
                continue
            await self._put(
                run, self._output(card), answer if self._usable(scene, answer) else scene
            )
        return StageReport()

    def _usable(self, scene: str, answer: str) -> bool:
        if self._checks.problems(answer):
            return False
        before, after = len(scene.split()), len(answer.split())
        return self.MIN_RATIO * before <= after <= self.MAX_RATIO * before

    async def _required(self, run: BookRun, name: str) -> str:
        data = await self._read(run, name)
        if data is None:
            raise ApplicationError(
                code="STAGE_INPUT_MISSING",
                message=f"stage {self._stage!r} needs {name}, which this run has not stored",
                http_status=409,
            )
        return data

    async def _read(self, run: BookRun, name: str) -> str | None:
        data = await asyncio.to_thread(self._artifacts.get, run.run_id, name)
        return None if data is None else data.decode("utf-8")

    async def _put(self, run: BookRun, name: str, text: str) -> None:
        await asyncio.to_thread(self._artifacts.put, run.run_id, name, text.encode("utf-8"))
