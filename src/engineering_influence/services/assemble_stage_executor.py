# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Assembles the drafted chapters into a manuscript the publishing pipeline can read."""

import asyncio
import re
import unicodedata

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.book_config_writer_interface import (
    BookConfigWriterInterface,
)
from engineering_influence.services.interfaces.chapter_cleaner_interface import (
    ChapterCleanerInterface,
)
from engineering_influence.services.interfaces.outline_parser_interface import (
    OutlineParserInterface,
)


class AssembleStageExecutor(StageExecutorInterface):
    """The ``assemble`` stage: no model call, only the files the typesetter reads.

    From ``outline.md`` and the ``chapter_NN.md`` files it writes, under ``manuscript/``, the project
    layout ``BookLoader`` expects: ``src/chapter_NN.md`` (each cleaned by ``ChapterCleaner`` and headed
    with the outline's title) and ``books/<slug>.toml`` (from ``BookConfigWriter``). The slug comes from
    the brief's title hint, or its idea, as lower-case letters, digits and hyphens. The title is the hint,
    or the idea's first line cut at 120 characters until a later stage sets a real one, with control
    characters taken out and runs of space made one (``Untitled`` if nothing is left). Nothing is written
    until every chapter has been cleaned, so a chapter that is refused leaves no half manuscript behind.

    The stage's own artifact is ``assemble.md``, a list of the files it wrote.

    The config has no author, publisher, edition, year or bio, which the author supplies, so the book is
    ready to load but not yet ready to build; see ``BookConfigWriter``.
    """

    STAGE = "assemble"
    ROOT = "manuscript"
    MAX_SLUG = 60
    MAX_TITLE = 120

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        outlines: OutlineParserInterface,
        cleaner: ChapterCleanerInterface,
        configs: BookConfigWriterInterface,
    ) -> None:
        self._artifacts = artifacts
        self._outlines = outlines
        self._cleaner = cleaner
        self._configs = configs

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Clean every chapter, then write the chapters, the config and the list of them."""
        outline_text = await self._read(run, "outline.md")
        if outline_text is None:
            raise self._missing(run, ["outline.md"])
        outline = self._outlines.parse(outline_text)
        names = [f"chapter_{chapter.number:02d}.md" for chapter in outline.chapters]
        texts = {name: await self._read(run, name) for name in names}
        absent = [name for name, text in texts.items() if text is None]
        if absent:
            raise self._missing(run, absent)
        brief = run.brief
        files: dict[str, str] = {}
        for chapter, name in zip(outline.chapters, names, strict=True):
            files[f"{self.ROOT}/src/{name}"] = self._cleaner.clean(
                chapter.number, chapter.title, texts[name] or ""
            )
        title = self._title(brief.title_hint, brief.idea)
        slug = self._slug(brief.title_hint or brief.idea)
        files[f"{self.ROOT}/books/{slug}.toml"] = self._configs.write(
            brief.kind.value, title, brief.trim_size, tuple(names)
        )
        for path, text in files.items():
            await asyncio.to_thread(self._artifacts.put, run.run_id, path, text.encode("utf-8"))
        listing = "# Manuscript\n\n" + "".join(f"- {path}\n" for path in files)
        await asyncio.to_thread(
            self._artifacts.put, run.run_id, f"{self.STAGE}.md", listing.encode("utf-8")
        )
        return StageReport()

    def _title(self, hint: str | None, idea: str) -> str:
        for candidate in (hint or "", idea):
            for line in candidate.splitlines():
                visible = "".join(" " if unicodedata.category(c)[0] == "C" else c for c in line)
                title = " ".join(visible.split())[: self.MAX_TITLE].rstrip()
                if title:
                    return title
        return "Untitled"

    def _slug(self, text: str) -> str:
        ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
        slug = re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")[: self.MAX_SLUG].strip("-")
        return slug or "book"

    async def _read(self, run: BookRun, name: str) -> str | None:
        data = await asyncio.to_thread(self._artifacts.get, run.run_id, name)
        return None if data is None else data.decode("utf-8")

    def _missing(self, run: BookRun, names: list[str]) -> ApplicationError:
        return ApplicationError(
            code="STAGE_INPUT_MISSING",
            message=f"stage {run.stage!r} needs {', '.join(names)}, which this run has not stored",
            http_status=409,
        )
