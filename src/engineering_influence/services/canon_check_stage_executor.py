# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The canon stage of a screenplay: the author's own canon check runs, and its findings become quality issues."""

import asyncio
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.canon_check_interface import CanonCheckInterface
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.canon_finding_parser_interface import (
    CanonFindingParserInterface,
)


class CanonCheckStageExecutor(StageExecutorInterface):
    """No model call. With no check configured the stage does nothing. Otherwise each finding is a quality issue, and
    an ERROR is blocking only when the run is set to block on canon errors; WARN findings never block.

    A check that exits without status 0 and prints nothing it can read is refused: a check that could not run must not
    read as a pass. The stage reports each finding in the author's words.
    """

    STAGE: ClassVar[str] = "check_canon"
    MAX_PROBLEMS_SHOWN: ClassVar[int] = 5

    def __init__(
        self,
        check: CanonCheckInterface | None,
        parser: CanonFindingParserInterface,
        blocking: bool,
    ) -> None:
        self._check = check
        self._parser = parser
        self._blocking = blocking

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Run the check, and report its findings; stop when a blocking ERROR is among them."""
        if self._check is None:
            return StageReport()
        status, output = await asyncio.to_thread(self._check.run)
        findings = self._parser.parse(output)
        if status != 0 and not findings:
            raise ApplicationError(
                code="STAGE_OUTPUT_INVALID",
                message=f"the canon check exited with status {status} and printed no finding it could read",
                http_status=422,
            )
        errors = [finding for finding in findings if finding.is_error()]
        if self._blocking and errors:
            shown = "; ".join(
                f"{finding.where}: [{finding.rule}] {finding.message}"
                for finding in errors[: self.MAX_PROBLEMS_SHOWN]
            )
            raise ApplicationError(
                code="STAGE_OUTPUT_INVALID",
                message=f"the canon check found {len(errors)} error(s): {shown}",
                http_status=422,
            )
        issues = tuple(
            QualityIssue(
                run.stage,
                "canon-finding",
                f"{finding.where}: [{finding.rule}] {finding.message}",
                blocking=False,
            )
            for finding in findings
        )
        return StageReport(issues)
