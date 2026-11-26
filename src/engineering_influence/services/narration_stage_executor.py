# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The optional non-Audible narration stage: each assembled chapter is read aloud by a narrator, gated, levelled and kept as WAV."""

import asyncio
import json
from typing import Any, ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.narrator_interface import NarratorInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.outline import Outline
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.narration_gate_interface import (
    NarrationGateInterface,
)
from engineering_influence.services.interfaces.narration_text_interface import (
    NarrationTextInterface,
)
from engineering_influence.services.interfaces.outline_parser_interface import (
    OutlineParserInterface,
)
from engineering_influence.services.narration_renderer import NarrationRenderer


class NarrationStageExecutor(StageExecutorInterface):
    """Narrates every chapter of the assembled manuscript, in order, and writes a manifest.

    **It is optional, and it can only help.** With no narrator the stage writes ``narration.json`` saying the book is not
    narrated and changes nothing else. With one, each chapter is read in segments (see ``NarrationText``), the segments
    joined with a short pause (see ``NarrationRenderer``), and the result is gated (see ``NarrationGate``). A chapter the
    gate refuses is not kept: it is recorded as ``AUDIO_REJECTED`` with the reasons, and a narrator that raises for a
    chapter records ``AUDIO_FAILED``. Neither stops the run, and neither puts audio in the book that the gate did not pass.

    A chapter is done when its record exists (``narrec_NN.json``), so a redelivered stage narrates only what is not
    done. The audio is 16-bit mono PCM WAV, ``narration/chapter_NN.wav``, levelled by the gate. Chapters are read from
    ``manuscript/src``, which ``assemble`` wrote.
    """

    STAGE: ClassVar[str] = "narration"
    MANIFEST: ClassVar[str] = "narration.json"
    DISCLOSURE: ClassVar[str] = (
        "This audiobook is narrated by a synthetic voice produced by a text-to-speech model, not by a human narrator."
    )

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        outlines: OutlineParserInterface,
        narrator: NarratorInterface | None,
        text: NarrationTextInterface,
        gate: NarrationGateInterface,
    ) -> None:
        self._artifacts = artifacts
        self._outlines = outlines
        self._narrator = narrator
        self._gate = gate
        self._renderer = NarrationRenderer(text)

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Narrate the chapters that are not done, then write the manifest."""
        narrator = self._narrator
        if narrator is None:
            await self._store(
                run, self.MANIFEST, json.dumps({"status": "not_narrated"}, indent=2) + "\n"
            )
            return StageReport()
        outline = self._outlines.parse(await self._required(run, "outline.md"))
        records = [await self._chapter(run, narrator, number) for number in self._numbers(outline)]
        await self._store(
            run,
            self.MANIFEST,
            json.dumps(
                {
                    "status": "narrated",
                    "ai_narration": True,
                    "disclosure": self.DISCLOSURE,
                    "chapters": records,
                },
                indent=2,
            )
            + "\n",
        )
        return StageReport(tuple(self._issues(records)))

    async def _chapter(
        self, run: BookRun, narrator: NarratorInterface, number: int
    ) -> dict[str, Any]:
        recorded = await self._read(run, self._record_name(number))
        if recorded is not None:
            loaded: dict[str, Any] = json.loads(recorded)
            return loaded
        record = await self._narrate(run, narrator, number)
        await self._store(
            run, self._record_name(number), json.dumps(record, ensure_ascii=False) + "\n"
        )
        return record

    async def _narrate(
        self, run: BookRun, narrator: NarratorInterface, number: int
    ) -> dict[str, Any]:
        source = await self._required(run, f"manuscript/src/chapter_{number:02d}.md")
        words = len(source.split())
        try:
            narration = self._renderer.render(narrator, source)
        except ApplicationError as error:
            return self._record(number, "failed", detail=error.message)
        problems = self._gate.problems(narration, words)
        if problems:
            return self._record(number, "rejected", detail="; ".join(problems))
        levelled = self._gate.normalise(narration)
        name = self._wav_name(number)
        if name not in await asyncio.to_thread(self._artifacts.names, run.run_id):
            await self._put(run, name, self._renderer.wav(levelled))
        return self._record(number, "narrated", seconds=round(levelled.seconds(), 1), words=words)

    @staticmethod
    def _record(number: int, status: str, **details: Any) -> dict[str, Any]:
        return {"chapter": number, "status": status, **details}

    def _issues(self, records: list[dict[str, Any]]) -> list[QualityIssue]:
        codes = {"rejected": "NARRATION_REJECTED", "failed": "NARRATION_FAILED"}
        issues: list[QualityIssue] = []
        for record in records:
            code = codes.get(record["status"])
            if code is not None:
                issues.append(
                    QualityIssue(
                        self.STAGE,
                        code,
                        f"chapter {record['chapter']}: {record['detail']}",
                        blocking=False,
                    )
                )
        return issues

    @staticmethod
    def _numbers(outline: Outline) -> list[int]:
        return [chapter.number for chapter in outline.chapters]

    @staticmethod
    def _record_name(number: int) -> str:
        return f"narrec_{number:02d}.json"

    @staticmethod
    def _wav_name(number: int) -> str:
        return f"narration/chapter_{number:02d}.wav"

    async def _required(self, run: BookRun, name: str) -> str:
        text = await self._read(run, name)
        if text is None:
            raise ApplicationError(
                code="STAGE_INPUT_MISSING",
                message=f"stage {run.stage!r} needs {name}, which this run has not stored",
                http_status=409,
            )
        return text

    async def _read(self, run: BookRun, name: str) -> str | None:
        data = await asyncio.to_thread(self._artifacts.get, run.run_id, name)
        return None if data is None else data.decode("utf-8")

    async def _store(self, run: BookRun, name: str, text: str) -> None:
        await self._put(run, name, text.encode("utf-8"))

    async def _put(self, run: BookRun, name: str, data: bytes) -> None:
        await asyncio.to_thread(self._artifacts.put, run.run_id, name, data)
