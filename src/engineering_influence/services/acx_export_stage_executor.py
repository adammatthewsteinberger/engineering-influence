# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The optional audiobook stage for ACX: each chapter as plain text, ready for Amazon's Virtual Voice.

The pipeline does not generate Audible narration. ACX prohibits unauthorized text-to-speech, and Virtual Voice is
Amazon's own narrator, run inside ACX by the rights holder. This stage prepares the text for that upload: markdown
taken out, headings kept as the first line of their chapter, one plain-text file per chapter and a manifest.
"""

import asyncio
import json
from typing import Any, ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.metadata_parser_interface import (
    MetadataParserInterface,
)
from engineering_influence.services.interfaces.narration_text_interface import (
    NarrationTextInterface,
)
from engineering_influence.services.interfaces.outline_parser_interface import (
    OutlineParserInterface,
)


class AcxExportStageExecutor(StageExecutorInterface):
    """Writes ``acx/chapter_NN.txt`` for every chapter of the assembled manuscript, and ``acx-export.json``.

    The manifest names the narrator the author must choose in ACX (Virtual Voice), so the record of what was prepared
    says who reads it. A chapter with no speakable words is reported as ``ACX_EMPTY_CHAPTER`` (non-blocking). A file
    that exists already is kept, so a redelivered stage writes the same bytes and does not rewrite them.
    """

    STAGE: ClassVar[str] = "audiobook"
    OPENING: ClassVar[str] = "acx/opening-credits.txt"
    CLOSING: ClassVar[str] = "acx/closing-credits.txt"
    SAMPLE: ClassVar[str] = "acx/retail-sample.txt"
    SAMPLE_WORDS: ClassVar[int] = 300
    MANIFEST: ClassVar[str] = "acx-export.json"
    NARRATOR: ClassVar[str] = "Amazon Virtual Voice, set up inside ACX"

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        outlines: OutlineParserInterface,
        text: NarrationTextInterface,
        metadata: MetadataParserInterface,
        author: str,
    ) -> None:
        self._artifacts = artifacts
        self._outlines = outlines
        self._text = text
        self._metadata = metadata
        self._author = author.strip()

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Export every chapter that is not written yet, then the manifest."""
        outline = self._outlines.parse(await self._required(run, "outline.md"))
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
            records.append(
                {
                    "chapter": number,
                    "heading": chapter.heading(),
                    "words": len(body.split()),
                    "file": name,
                }
            )
        title = self._metadata.parse(await self._required(run, "metadata.md")).title
        opening, closing = self._credits(title)
        await self._put_once(run, self.OPENING, opening)
        await self._put_once(run, self.CLOSING, closing)
        first = await self._required(run, self._source(outline.chapters[0].number))
        words = " ".join(self._text.segments(first)).split()
        sample = " ".join(words[: self.SAMPLE_WORDS])
        await self._put_once(run, self.SAMPLE, sample + "\n")
        manifest = {
            "status": "exported",
            "narrator": self.NARRATOR,
            "review_before_upload": True,
            "opening_credits": self.OPENING,
            "closing_credits": self.CLOSING,
            "retail_sample": self.SAMPLE,
            "retail_sample_words": len(sample.split()),
            "chapters": records,
        }
        await self._store(
            run, self.MANIFEST, json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        )
        return StageReport(tuple(issues))

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
        await asyncio.to_thread(self._artifacts.put, run.run_id, name, text.encode("utf-8"))
