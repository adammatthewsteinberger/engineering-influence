# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The optional audiobook stage for ACX: each part as text and as audio, ready for an upload the author decides on.

Virtual Voice is Amazon's narrator inside ACX, and it is available only after the author applies for access, so this
stage does not assume it. It writes two things for every part of the book: the plain text (the script for Virtual
Voice, should access be granted) and an audio file read by the narrator the author configured (``EI_NARRATOR``).

ACX prohibits unauthorized text-to-speech. The manifest says so, and nothing here uploads anything: the author reads the
terms with ACX and decides what, if anything, to upload.
"""

import asyncio
import json
from typing import Any, ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.narrator_interface import NarratorInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.metadata_parser_interface import (
    MetadataParserInterface,
)
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
from engineering_influence.services.narration_stage_executor import NarrationStageExecutor


class AcxExportStageExecutor(StageExecutorInterface):
    """Writes the text and the audio of every part of the book, and ``acx-export.json``.

    Parts are the opening credits, each chapter, the closing credits and the retail sample (the first 300 words). Text
    goes to ``acx/``; audio goes to ``acx/audio/`` as 16-bit mono WAV, read by the narrator and kept only when the gate
    passes it. With no narrator the audio is not made and the manifest says so. A part whose audio the gate refuses is
    reported as ``ACX_AUDIO_REJECTED``, and one whose narrator raises as ``ACX_AUDIO_FAILED``; both are non-blocking. A
    file that exists already is kept, so a redelivered stage writes the same bytes.
    """

    STAGE: ClassVar[str] = "audiobook"
    OPENING: ClassVar[str] = "acx/opening-credits.txt"
    CLOSING: ClassVar[str] = "acx/closing-credits.txt"
    SAMPLE: ClassVar[str] = "acx/retail-sample.txt"
    SAMPLE_WORDS: ClassVar[int] = 300
    AUDIO_DIR: ClassVar[str] = "acx/audio"
    MANIFEST: ClassVar[str] = "acx-export.json"
    ACX_POLICY: ClassVar[str] = (
        "ACX prohibits unauthorized text-to-speech. Read ACX's current terms before uploading any audio made here."
    )
    VIRTUAL_VOICE: ClassVar[str] = (
        "Amazon Virtual Voice is available only after the author applies for access inside ACX. The text files are the "
        "script for it; nothing assumes access has been granted."
    )

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        outlines: OutlineParserInterface,
        text: NarrationTextInterface,
        metadata: MetadataParserInterface,
        author: str,
        narrator: NarratorInterface | None,
        gate: NarrationGateInterface,
    ) -> None:
        """Remember the artifacts, outlines, text, metadata and author the export is written from."""
        self._artifacts = artifacts
        self._outlines = outlines
        self._text = text
        self._metadata = metadata
        self._author = author.strip()
        self._narrator = narrator
        self._gate = gate
        self._renderer = NarrationRenderer(text)

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Export every part that is not written yet, then the manifest."""
        outline = self._outlines.parse(await self._required(run, "outline.md"))
        narrator = self._narrator
        records: list[dict[str, Any]] = []
        issues: list[QualityIssue] = []
        for chapter in outline.chapters:
            number = chapter.number
            body = "\n\n".join(self._text.segments(await self._required(run, self._source(number))))
            if not body:
                issues.append(
                    QualityIssue(
                        self.STAGE,
                        "ACX_EMPTY_CHAPTER",
                        f"chapter {number} has no speakable words",
                        blocking=False,
                    )
                )
            name = self._export(number)
            if name not in await asyncio.to_thread(self._artifacts.names, run.run_id):
                await self._store(run, name, body + "\n")
            audio = await self._audio(run, narrator, f"chapter_{number:02d}", body)
            records.append(
                {
                    "chapter": number,
                    "heading": chapter.heading(),
                    "words": len(body.split()),
                    "file": name,
                    "audio": audio,
                }
            )
        title = self._metadata.parse(await self._required(run, "metadata.md")).title
        opening, closing = self._credits(title)
        await self._put_once(run, self.OPENING, opening)
        await self._put_once(run, self.CLOSING, closing)
        first = await self._required(run, self._source(outline.chapters[0].number))
        words = " ".join(self._text.segments(first)).split()
        sample = " ".join(words[: self.SAMPLE_WORDS]) + "\n"
        await self._put_once(run, self.SAMPLE, sample)
        parts = [
            await self._audio(run, narrator, "opening-credits", opening),
            await self._audio(run, narrator, "closing-credits", closing),
            await self._audio(run, narrator, "retail-sample", sample),
        ]
        issues.extend(self._issues([*parts, *(record["audio"] for record in records)]))
        manifest = {
            "status": "exported",
            "virtual_voice": self.VIRTUAL_VOICE,
            "acx_policy": self.ACX_POLICY,
            "review_before_upload": True,
            "text": {
                "opening_credits": self.OPENING,
                "closing_credits": self.CLOSING,
                "retail_sample": self.SAMPLE,
                "retail_sample_words": len(sample.split()),
            },
            "audio": self._audio_manifest(narrator),
            "chapters": records,
            "opening_credits_audio": parts[0],
            "closing_credits_audio": parts[1],
            "retail_sample_audio": parts[2],
        }
        await self._store(
            run, self.MANIFEST, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        )
        return StageReport(tuple(issues))

    def _audio_manifest(self, narrator: NarratorInterface | None) -> dict[str, Any]:
        if narrator is None:
            return {"status": "not_narrated", "reason": "no narrator is configured (EI_NARRATOR)"}
        return {
            "status": "narrated",
            "ai_narration": True,
            "disclosure": NarrationStageExecutor.DISCLOSURE,
            "format": "16-bit mono WAV; check ACX's accepted format before upload",
        }

    async def _audio(
        self, run: BookRun, narrator: NarratorInterface | None, stem: str, text: str
    ) -> dict[str, Any]:
        """One part's audio: rendered, gated and kept, or a record of why not."""
        if narrator is None:
            return {"part": stem, "file": None, "status": "not_narrated"}
        name = f"{self.AUDIO_DIR}/{stem}.wav"
        words = len(text.split())
        # The record has the same shape whether the audio was just made or was made by an earlier delivery, so a
        # redelivered manifest is byte-for-byte the one already stored.
        if name in await asyncio.to_thread(self._artifacts.names, run.run_id):
            return {"part": stem, "file": name, "status": "narrated", "words": words}
        try:
            narration = self._renderer.render(narrator, text)
        except ApplicationError as error:
            return {"part": stem, "file": None, "status": "failed", "detail": error.message}
        problems = self._gate.problems(narration, words)
        if problems:
            return {"part": stem, "file": None, "status": "rejected", "detail": "; ".join(problems)}
        levelled = self._gate.normalise(narration)
        await self._put(run, name, self._renderer.wav(levelled))
        return {"part": stem, "file": name, "status": "narrated", "words": words}

    @staticmethod
    def _issues(parts: list[dict[str, Any]]) -> list[QualityIssue]:
        issues: list[QualityIssue] = []
        for part in parts:
            if part["status"] == "rejected":
                issues.append(
                    QualityIssue(
                        AcxExportStageExecutor.STAGE,
                        "ACX_AUDIO_REJECTED",
                        f"{part['part']}: {part['detail']}",
                        blocking=False,
                    )
                )
            elif part["status"] == "failed":
                issues.append(
                    QualityIssue(
                        AcxExportStageExecutor.STAGE,
                        "ACX_AUDIO_FAILED",
                        f"{part['part']}: {part['detail']}",
                        blocking=False,
                    )
                )
        return issues

    def _credits(self, title: str) -> tuple[str, str]:
        """Draft credits from the title and the author's name. The narrator line is left to ACX and the author."""
        byline = f", written by {self._author}" if self._author else ""
        return f"{title}{byline}.\n", f"You have been listening to {title}{byline}.\n"

    async def _put_once(self, run: BookRun, name: str, text: str) -> None:
        if name not in await asyncio.to_thread(self._artifacts.names, run.run_id):
            await self._store(run, name, text)

    @staticmethod
    def _source(number: int) -> str:
        return f"manuscript/src/chapter_{number:02d}.md"

    @staticmethod
    def _export(number: int) -> str:
        return f"acx/chapter_{number:02d}.txt"

    async def _required(self, run: BookRun, name: str) -> str:
        data = await asyncio.to_thread(self._artifacts.get, run.run_id, name)
        if data is None:
            raise ApplicationError(
                code="STAGE_INPUT_MISSING",
                message=f"stage {run.stage!r} needs {name}, which this run has not stored",
                http_status=409,
            )
        return data.decode("utf-8")

    async def _store(self, run: BookRun, name: str, text: str) -> None:
        await self._put(run, name, text.encode("utf-8"))

    async def _put(self, run: BookRun, name: str, data: bytes | str) -> None:
        payload = data.encode("utf-8") if isinstance(data, str) else data
        await asyncio.to_thread(self._artifacts.put, run.run_id, name, payload)
