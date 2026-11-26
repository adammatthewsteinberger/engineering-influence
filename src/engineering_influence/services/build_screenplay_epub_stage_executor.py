# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The EPUB stage of a screenplay: the script becomes one EPUB page, which must pass epubcheck."""

import asyncio
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.screenplay_epub_writer_interface import (
    ScreenplayEpubWriterInterface,
)
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.screenplay_epub_package_interface import (
    ScreenplayEpubPackageInterface,
)


class BuildScreenplayEpubStageExecutor(StageExecutorInterface):
    """Stores `screenplay.epub`. An EPUB epubcheck rejects is not stored: the stage stops and names the first findings,
    because a reader would not open a file that fails the format."""

    STAGE: ClassVar[str] = "build_epub"
    SCRIPT: ClassVar[str] = "screenplay.fountain"
    EPUB: ClassVar[str] = "screenplay.epub"
    MAX_PROBLEMS_SHOWN: ClassVar[int] = 5

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        package: ScreenplayEpubPackageInterface,
        writer: ScreenplayEpubWriterInterface,
    ) -> None:
        self._artifacts = artifacts
        self._package = package
        self._writer = writer

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Write the EPUB, check it, and store it."""
        script = await self._required(run)
        data, problems = await asyncio.to_thread(self._writer.write, self._package.entries(script))
        if problems:
            raise ApplicationError(
                code="STAGE_OUTPUT_INVALID",
                message="the screenplay EPUB fails epubcheck: "
                + "; ".join(problems[: self.MAX_PROBLEMS_SHOWN]),
                http_status=422,
            )
        await asyncio.to_thread(self._artifacts.put, run.run_id, self.EPUB, data)
        return StageReport()

    async def _required(self, run: BookRun) -> str:
        data = await asyncio.to_thread(self._artifacts.get, run.run_id, self.SCRIPT)
        if data is None:
            raise ApplicationError(
                code="STAGE_INPUT_MISSING",
                message=f"stage {run.stage!r} needs {self.SCRIPT}, which this run has not stored",
                http_status=409,
            )
        return data.decode("utf-8")
