# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Audits the assembled book with the publishing pipeline's own gates."""

import asyncio

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.manuscript_auditor_interface import (
    ManuscriptAuditorInterface,
)
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.manuscript_project_interface import (
    ManuscriptProjectInterface,
)


class AuditStageExecutor(StageExecutorInterface):
    """The ``audit`` stage: no model call, the existing gates run on what ``assemble`` wrote.

    It reads the ``manuscript/`` files through ``ManuscriptProject`` (the config under ``books/`` and the chapters
    under ``src/``), gives them to a ``ManuscriptAuditorInterface`` as a project, and stores what comes back under ``audit/``: the manuscript
    audit, the release readiness report and the publication report. It then writes ``audit.md``, the status, the
    errors and the warnings.

    **The reports are stored before anything is raised**, so a book that fails can be read. A book with errors
    stops the run with ``AUDIT_FAILED`` and every error in the message. Warnings do not stop it; a book
    without prices, which are the author's to set, passes with a warning for each.
    """

    STAGE = "audit"

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        auditor: ManuscriptAuditorInterface,
        project: ManuscriptProjectInterface,
    ) -> None:
        """Remember the artifacts, the manuscript auditor and the project the gates run on."""
        self._artifacts = artifacts
        self._auditor = auditor
        self._project = project

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Audit the assembled book and store the reports."""
        files, slug = await self._project.load(run)
        audit = await asyncio.to_thread(self._auditor.audit, files, slug)
        for name, data in audit.files:
            await asyncio.to_thread(self._artifacts.put, run.run_id, f"audit/{name}", data)
        summary = (
            f"# Audit\n\nStatus: {audit.status}\n\n"
            f"{self._section('Errors', audit.errors)}\n{self._section('Warnings', audit.warnings)}"
        )
        await asyncio.to_thread(
            self._artifacts.put, run.run_id, f"{self.STAGE}.md", summary.encode("utf-8")
        )
        if not audit.passed:
            raise ApplicationError(
                code="AUDIT_FAILED",
                message=f"the assembled book {slug!r} did not pass its audit: "
                + "; ".join(audit.errors),
                http_status=422,
            )
        return StageReport()

    @staticmethod
    def _section(title: str, items: tuple[str, ...]) -> str:
        return f"## {title}\n\n" + ("".join(f"- {item}\n" for item in items) or "None.\n")
