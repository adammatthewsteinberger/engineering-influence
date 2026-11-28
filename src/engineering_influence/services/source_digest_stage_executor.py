# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The digest stage of a screenplay: each source file is condensed once, so the outline reads the digests, not the whole book."""

import asyncio
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.source_digester_interface import SourceDigesterInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.stage_report import StageReport


class SourceDigestStageExecutor(StageExecutorInterface):
    """Each `source/NNN.md` becomes `digest/NNN.md`. A digest that is already stored is kept, so a stage that runs
    again condenses only what is missing. No file is written for a source the model has not finished."""

    STAGE: ClassVar[str] = "digest_sources"
    SOURCES: ClassVar[str] = "source/"
    DIGESTS: ClassVar[str] = "digest/"

    def __init__(
        self, artifacts: ArtifactStoreInterface, digester: SourceDigesterInterface
    ) -> None:
        """Remember the artifacts and the digester each source is condensed with."""
        self._artifacts = artifacts
        self._digester = digester

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Condense each source that has no digest yet, and store the digest."""
        names = await asyncio.to_thread(self._artifacts.names, run.run_id)
        sources = sorted(name for name in names if name.startswith(self.SOURCES))
        if not sources:
            raise ApplicationError(
                code="STAGE_INPUT_MISSING",
                message=f"stage {run.stage!r} needs the source files, which this run has not stored",
                http_status=409,
            )
        for name in sources:
            digest = self.DIGESTS + name.removeprefix(self.SOURCES)
            if await asyncio.to_thread(self._artifacts.get, run.run_id, digest) is not None:
                continue
            data = await asyncio.to_thread(self._artifacts.get, run.run_id, name)
            text = await asyncio.to_thread(
                self._digester.digest, run, (data or b"").decode("utf-8")
            )
            await asyncio.to_thread(self._artifacts.put, run.run_id, digest, text.encode("utf-8"))
        return StageReport()
