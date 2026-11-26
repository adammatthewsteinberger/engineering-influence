# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The render stage of a screenplay: the assembled script becomes a PDF, and its page count is checked against the length."""

import asyncio
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.screenplay_typesetter_interface import (
    ScreenplayTypesetterInterface,
)
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.screenplay_latex_source_interface import (
    ScreenplayLatexSourceInterface,
)
from engineering_influence.services.interfaces.screenplay_length_interface import (
    ScreenplayLengthInterface,
)
from engineering_influence.services.screenplay_length import ScreenplayLength


class RenderScreenplayStageExecutor(StageExecutorInterface):
    """Stores `screenplay.pdf` and `render.md` (the page count and the length notes).

    **A script that does not typeset stops the stage**, with the last lines of LaTeX's log in the message, because a
    screenplay without its PDF is not a finished screenplay. **A script over the page ceiling stops it too** (the
    length gate's error); a script past three hours is a tolerated note, so the author sees it and the run still
    finishes. The page count is the rendered PDF's, which is what the length is measured in.
    """

    STAGE: ClassVar[str] = "render_script"
    SCRIPT: ClassVar[str] = "screenplay.fountain"
    SHOOTING_SCRIPT: ClassVar[str] = "shooting_script.fountain"
    PDF: ClassVar[str] = "screenplay.pdf"
    REPORT: ClassVar[str] = "render.md"

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        source: ScreenplayLatexSourceInterface,
        typesetter: ScreenplayTypesetterInterface,
        length: ScreenplayLengthInterface,
    ) -> None:
        self._artifacts = artifacts
        self._source = source
        self._typesetter = typesetter
        self._length = length

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Typeset the script, check its length, and store the PDF and the report."""
        script = await self._printed_script(run)
        result = await asyncio.to_thread(self._typesetter.typeset, self._source.render(script))
        if result.status != 0:
            raise ApplicationError(
                code="STAGE_OUTPUT_INVALID",
                message=f"LaTeX could not typeset the screenplay:\n{result.log}",
                http_status=422,
            )
        problems = self._length.problems(result.pages)
        if problems and result.pages > ScreenplayLength.CEILING_PAGES:
            raise ApplicationError(
                code="STAGE_OUTPUT_INVALID",
                message="; ".join(problems),
                http_status=422,
            )
        await self._put(run, self.PDF, result.pdf)
        await self._put(run, self.REPORT, f"# Render\n\n- pages: {result.pages}\n")
        issues = tuple(
            QualityIssue(run.stage, "screenplay-length", problem, blocking=False)
            for problem in problems
        )
        return StageReport(issues)

    async def _printed_script(self, run: BookRun) -> str:
        """The locked script with its scene numbers when the lock stage stored one, otherwise the plain script."""
        numbered = await asyncio.to_thread(self._artifacts.get, run.run_id, self.SHOOTING_SCRIPT)
        if numbered is not None:
            return numbered.decode("utf-8")
        return await self._required(run, self.SCRIPT)

    async def _required(self, run: BookRun, name: str) -> str:
        data = await asyncio.to_thread(self._artifacts.get, run.run_id, name)
        if data is None:
            raise ApplicationError(
                code="STAGE_INPUT_MISSING",
                message=f"stage {run.stage!r} needs {name}, which this run has not stored",
                http_status=409,
            )
        return data.decode("utf-8")

    async def _put(self, run: BookRun, name: str, data: bytes | str) -> None:
        body = data.encode("utf-8") if isinstance(data, str) else data
        await asyncio.to_thread(self._artifacts.put, run.run_id, name, body)
