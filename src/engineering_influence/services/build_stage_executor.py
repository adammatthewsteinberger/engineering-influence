# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Builds the assembled book into its finished files, and says how well it came out."""

import asyncio

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.artifact_store_interface import ArtifactStoreInterface
from engineering_influence.interfaces.manuscript_builder_interface import (
    ManuscriptBuilderInterface,
)
from engineering_influence.interfaces.stage_executor_interface import StageExecutorInterface
from engineering_influence.models.book_run import BookRun
from engineering_influence.models.manuscript_build import ManuscriptBuild
from engineering_influence.models.stage_report import StageReport
from engineering_influence.services.interfaces.manuscript_project_interface import (
    ManuscriptProjectInterface,
)
from engineering_influence.services.interfaces.quality_report_interface import (
    QualityReportInterface,
)


class BuildStageExecutor(StageExecutorInterface):
    """The ``build`` stage: no model call; the whole publishing pipeline runs on what ``assemble`` wrote.

    It builds the interior PDF, the covers and the EPUB, verifies each, checks the release as a strict release,
    and packages the KDP bundle. It stores the bundle's files under ``book/`` (the finished interior, EPUB and
    covers, ``listing.md`` and ``MANIFEST.json``) and the build's evidence under ``build/`` (the publication
    report and the step logs). It then writes ``quality-report.json`` and ``build.md``.

    **Everything is stored before anything is raised**, so a book that fails can be read. A book that does not
    pass stops the run with ``BUILD_FAILED`` and every error in the message.
    """

    STAGE = "build"

    def __init__(
        self,
        artifacts: ArtifactStoreInterface,
        builder: ManuscriptBuilderInterface,
        project: ManuscriptProjectInterface,
        quality: QualityReportInterface,
    ) -> None:
        self._artifacts = artifacts
        self._builder = builder
        self._project = project
        self._quality = quality

    async def execute(self, run: BookRun, attempt: int) -> StageReport:
        """Build the book and store what came of it."""
        files, slug = await self._project.load(run)
        build = await asyncio.to_thread(self._builder.build, files, slug)
        for name, data in build.book:
            await self._put(run, f"book/{name}", data)
        for name, data in build.reports:
            await self._put(run, f"build/{name}", data)
        report = self._quality.render(slug, run.issues, build)
        await self._put(run, "quality-report.json", report)
        await self._put(run, f"{self.STAGE}.md", self._summary(build).encode("utf-8"))
        if not build.passed:
            raise ApplicationError(
                code="BUILD_FAILED",
                message=f"the book {slug!r} did not build and pass its release check: "
                + "; ".join(build.errors),
                http_status=422,
            )
        return StageReport()

    async def _put(self, run: BookRun, name: str, data: bytes) -> None:
        await asyncio.to_thread(self._artifacts.put, run.run_id, name, data)

    @staticmethod
    def _summary(build: ManuscriptBuild) -> str:
        def section(title: str, items: list[str]) -> str:
            return f"## {title}\n\n" + ("".join(f"- {item}\n" for item in items) or "None.\n")

        steps = [f"{name}: {status}" for name, status in build.steps]
        return (
            f"# Build\n\nStatus: {build.status}\n\n{section('Steps', steps)}\n"
            f"{section('Errors', list(build.errors))}\n{section('Warnings', list(build.warnings))}"
        )
