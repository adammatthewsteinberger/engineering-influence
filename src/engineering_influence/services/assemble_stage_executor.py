# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Assembles the drafted chapters into a manuscript the publishing pipeline can read."""

import asyncio
import re
import unicodedata

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.author_profile import AuthorProfile
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.book_config_writer_interface import (
    BookConfigWriterInterface,
)
from engineering_influence.services.interfaces.chapter_cleaner_interface import (
    ChapterCleanerInterface,
)
from engineering_influence.services.interfaces.metadata_parser_interface import (
    MetadataParserInterface,
)
from engineering_influence.services.interfaces.outline_parser_interface import (
    OutlineParserInterface,
)


class AssembleStageExecutor(StageExecutorInterface):
    """The ``assemble`` stage: no model call, only the files the typesetter reads.

    From ``outline.md``, ``metadata.md`` and the chapter files of the last editing pass (``<source>_NN.md``, where the
    source prefix is the one the runtime names) it writes, under ``manuscript/``, the
    project layout ``BookLoader`` expects: ``src/chapter_NN.md`` (each cleaned by ``ChapterCleaner`` and
    headed with the outline's title) and ``books/<slug>.toml`` (from ``BookConfigWriter``: the listing from the
    metadata stage and, when ``EI_AUTHOR_PROFILE`` named one, the author's details). The slug is the
    listing's title as lower-case letters, digits and hyphens. Nothing is written until every chapter has
    been cleaned, so a chapter that is refused leaves no half manuscript behind.

    The stage's own artifact is ``assemble.md``, a list of the files it wrote.

    Without an author profile the config has no author, publisher, edition, year or bio, so the book loads
    but does not build until they are added; see ``AuthorProfile``.
    """

    STAGE = "assemble"
    ROOT = "manuscript"
    MAX_SLUG = 60

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        outlines: OutlineParserInterface,
        metadata: MetadataParserInterface,
        cleaner: ChapterCleanerInterface,
        configs: BookConfigWriterInterface,
        profile: AuthorProfile | None,
        source: str,
    ) -> None:
        """Remember the artifacts, outlines, metadata, chapter cleaner and config the assembled book is written from."""
        self._artifacts = artifacts
        self._outlines = outlines
        self._metadata = metadata
        self._cleaner = cleaner
        self._configs = configs
        self._profile = profile
        self._source = source

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Clean every chapter, then write the chapters, the config and the list of them."""
        outline_text = await self._read(run, "outline.md")
        metadata_text = await self._read(run, "metadata.md")
        if outline_text is None or metadata_text is None:
            absent = [
                name
                for name, text in (("outline.md", outline_text), ("metadata.md", metadata_text))
                if text is None
            ]
            raise self._missing(run, absent)
        outline = self._outlines.parse(outline_text)
        metadata = self._metadata.parse(metadata_text)
        names = [f"chapter_{chapter.number:02d}.md" for chapter in outline.chapters]
        sources = {
            name: f"{self._source}_{chapter.number:02d}.md"
            for name, chapter in zip(names, outline.chapters, strict=True)
        }
        texts = {name: await self._read(run, source) for name, source in sources.items()}
        lost = [sources[name] for name, text in texts.items() if text is None]
        if lost:
            raise self._missing(run, lost)
        brief = run.brief
        files: dict[str, str] = {}
        for chapter, name in zip(outline.chapters, names, strict=True):
            files[f"{self.ROOT}/src/{name}"] = self._cleaner.clean(
                chapter.number, chapter.title, texts[name] or ""
            )
        files[f"{self.ROOT}/books/{self._slug(metadata.title)}.toml"] = self._configs.write(
            brief.kind.value, metadata, self._profile, brief.trim_size, tuple(names)
        )
        for path, text in files.items():
            await asyncio.to_thread(self._artifacts.put, run.run_id, path, text.encode("utf-8"))
        listing = "# Manuscript\n\n" + "".join(f"- {path}\n" for path in files)
        await asyncio.to_thread(
            self._artifacts.put, run.run_id, f"{self.STAGE}.md", listing.encode("utf-8")
        )
        return StageReport()

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
