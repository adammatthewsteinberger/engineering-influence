# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The outline stage of an audiobook run: each finished chapter becomes a chapter of the manuscript, and the outline the narrator reads is built from the chapters themselves, with no model call."""

import asyncio
import re
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.stage_report import StageReport


class AudiobookOutlineStageExecutor(StageExecutorInterface):
    """Each `source/NNN.md` is one chapter, numbered in name order. Its first `#` heading is its title, its first sentence
    is its purpose, and the first sentence of each paragraph is one of its beats. The chapter is stored as
    `manuscript/src/chapter_NN.md` and the outline as `outline.md`, in the form the outline parser reads.
    """

    STAGE: ClassVar[str] = "audiobook_outline"
    MAX_BEATS: ClassVar[int] = 40
    MAX_PURPOSE_CHARACTERS: ClassVar[int] = 300
    SENTENCE: ClassVar[re.Pattern[str]] = re.compile(r"(?<=[.!?])\s+")

    def __init__(self, artifacts: ArtifactStoreInterface) -> None:
        """Remember the artifacts the audiobook outline is read from and written to."""
        self._artifacts = artifacts

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Store each chapter and the outline built from them."""
        names = await asyncio.to_thread(self._artifacts.names, run.run_id)
        sources = sorted(name for name in names if name.startswith("source/"))
        if not sources:
            raise ApplicationError(
                code="STAGE_INPUT_MISSING",
                message=f"stage {run.stage!r} needs the chapter files, which this run has not stored",
                http_status=409,
            )
        blocks: list[str] = []
        for number, name in enumerate(sources, 1):
            data = await asyncio.to_thread(self._artifacts.get, run.run_id, name)
            text = (data or b"").decode("utf-8")
            await asyncio.to_thread(
                self._artifacts.put,
                run.run_id,
                f"manuscript/src/chapter_{number:02d}.md",
                text.encode("utf-8"),
            )
            blocks.append(self._block(number, text, last=number == len(sources)))
        await asyncio.to_thread(
            self._artifacts.put, run.run_id, "outline.md", "\n".join(blocks).encode("utf-8")
        )
        return StageReport()

    def _block(self, number: int, text: str, last: bool) -> str:
        title = next(
            (line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("# ")), ""
        )
        paragraphs = [
            " ".join(p.split())
            for p in re.split(r"\n\s*\n", text)
            if p.strip() and not p.lstrip().startswith("#")
        ]
        if not paragraphs:
            raise ApplicationError(
                code="STAGE_INPUT_MISSING",
                message=f"chapter {number} has no text to narrate",
                http_status=422,
            )
        purpose = self.SENTENCE.split(paragraphs[0])[0][: self.MAX_PURPOSE_CHARACTERS]
        beats = [self.SENTENCE.split(p)[0] for p in paragraphs[: self.MAX_BEATS]]
        leads = "the end of the book" if last else f"chapter {number + 1}"
        lines = [
            f"## Chapter {number}: {title or f'Chapter {number}'}",
            f"Purpose: {purpose}",
            "Beats:",
            *(f"- {beat}" for beat in beats),
            f"Leads to: {leads}.",
            "",
        ]
        return "\n".join(lines)
