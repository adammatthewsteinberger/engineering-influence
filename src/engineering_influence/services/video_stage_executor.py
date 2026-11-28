# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The video stage of a screenplay: each shot is generated with a hosted model, priced before the first paid call."""

import asyncio
import json
from typing import Any, ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.spend_consent_needed_error import SpendConsentNeededError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.interfaces.video_generator_interface import VideoGeneratorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.stage_report import StageReport
from engineering_influence.models.video_shot import VideoShot
from engineering_influence.services.interfaces.shot_list_builder_interface import (
    ShotListBuilderInterface,
)
from engineering_influence.services.interfaces.video_cost_interface import VideoCostInterface


class VideoStageExecutor(StageExecutorInterface):
    """Stores `video/shot_NNN.mp4` for each shot and `video/manifest.json` marking the film as AI-generated.

    Without a configured provider the stage stores a `not_generated` manifest and spends nothing. With one, it prices the
    shots not yet stored; if they do not fit the run's budget it stops with SpendConsentNeededError, so the run waits for
    the maintainer's consent instead of spending past the cap. A shot already stored is never generated again.
    """

    STAGE: ClassVar[str] = "video"
    SCRIPT: ClassVar[str] = "screenplay.fountain"
    SHOOTING_SCRIPT: ClassVar[str] = "shooting_script.fountain"
    MANIFEST: ClassVar[str] = "video/manifest.json"

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        builder: ShotListBuilderInterface,
        cost: VideoCostInterface,
        generator: VideoGeneratorInterface | None,
    ) -> None:
        """Remember the artifacts, shot planner, cost estimator and the optional video generator."""
        self._artifacts = artifacts
        self._builder = builder
        self._cost = cost
        self._generator = generator

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Plan the shots from the script, then generate and store the ones still missing."""
        script = await self._script(run)
        shots = await asyncio.to_thread(self._builder.build, script)
        if self._generator is None:
            if await asyncio.to_thread(self._artifacts.get, run.run_id, self.MANIFEST) is None:
                await self._store_manifest(run, self._not_generated(shots))
            return StageReport()
        stored = set(await asyncio.to_thread(self._artifacts.names, run.run_id))
        pending = tuple(shot for shot in shots if self._name(shot) not in stored)
        cost = self._cost.cost_micro_usd(pending)
        remaining = run.budget.remaining()
        if cost > remaining:
            raise SpendConsentNeededError(cost - remaining)
        for shot in pending:
            data = await asyncio.to_thread(self._generator.generate, shot)
            await asyncio.to_thread(self._artifacts.put, run.run_id, self._name(shot), data)
        await self._store_manifest(run, self._generated(shots))
        return StageReport()

    async def _script(self, run: BookRun) -> str:
        """The locked script with its scene numbers when the lock stage stored one, otherwise the plain script."""
        numbered = await asyncio.to_thread(self._artifacts.get, run.run_id, self.SHOOTING_SCRIPT)
        if numbered is not None:
            return numbered.decode("utf-8")
        data = await asyncio.to_thread(self._artifacts.get, run.run_id, self.SCRIPT)
        if data is None:
            raise ApplicationError(
                code="STAGE_INPUT_MISSING",
                message=f"stage {self.STAGE!r} needs {self.SCRIPT}, which this run has not stored",
                http_status=409,
            )
        return data.decode("utf-8")

    async def _store_manifest(self, run: BookRun, manifest: dict[str, Any]) -> None:
        data = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
        await asyncio.to_thread(self._artifacts.put, run.run_id, self.MANIFEST, data)

    def _generated(self, shots: tuple[VideoShot, ...]) -> dict[str, Any]:
        return {
            "ai_generated": True,
            "estimated_micro_usd": self._cost.cost_micro_usd(shots),
            "shots": [self._entry(shot) for shot in shots],
            "status": "generated",
        }

    def _not_generated(self, shots: tuple[VideoShot, ...]) -> dict[str, Any]:
        return {
            "ai_generated": False,
            "reason": "no video provider is configured",
            "shots": [self._entry(shot) for shot in shots],
            "status": "not_generated",
        }

    @staticmethod
    def _entry(shot: VideoShot) -> dict[str, Any]:
        return {
            "file": VideoStageExecutor._name(shot),
            "model": shot.model(),
            "number": shot.number,
            "scene": shot.scene,
            "seconds": shot.seconds(),
        }

    @staticmethod
    def _name(shot: VideoShot) -> str:
        return f"video/shot_{shot.number:03d}.mp4"
