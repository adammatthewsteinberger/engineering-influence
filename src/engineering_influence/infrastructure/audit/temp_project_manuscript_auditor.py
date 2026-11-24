# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Audits a book by laying its files out as a project in a scratch folder and running the pipeline on it."""

import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path

from engineering_influence.infrastructure.audit.publication_findings import PublicationFindings
from engineering_influence.infrastructure.scratch_project import ScratchProject
from engineering_influence.interfaces.manuscript_auditor_interface import (
    ManuscriptAuditorInterface,
)
from engineering_influence.interfaces.publish_pipeline_interface import PublishPipelineInterface
from engineering_influence.models.manuscript_audit import ManuscriptAudit


class TempProjectManuscriptAuditor(ManuscriptAuditorInterface):
    """Writes the files into a new temporary folder, runs the audit gates there, reads the reports back and removes the folder.

    The gates are ``PublishPipeline.publish(..., audit_only=True)``: the manuscript audit and the release
    readiness check, which need no TeX toolchain and no cover. The folder is private to the call and is removed
    when it ends, so nothing of the book is left on disk. A file whose path would leave the folder is
    refused before anything is written.
    """

    REPORTS = ("manuscript-audit.json", "release-readiness.json", "publication-report.json")

    def __init__(self, pipelines: Callable[[Path], PublishPipelineInterface]) -> None:
        self._pipelines = pipelines

    def audit(self, files: Mapping[str, bytes], slug: str) -> ManuscriptAudit:
        """The audit of the book."""
        with tempfile.TemporaryDirectory(prefix="ei-audit-") as scratch:
            root = Path(scratch).resolve()
            ScratchProject.write(root, files)
            result, passed = self._pipelines(root).publish(slug, audit_only=True)
            release = root / "build" / slug / "release"
            reports = tuple(
                (name, (release / name).read_bytes())
                for name in self.REPORTS
                if (release / name).is_file()
            )
        return ManuscriptAudit(
            passed=passed,
            status=str(result["status"]),
            errors=PublicationFindings.errors(result),
            warnings=PublicationFindings.warnings(result),
            files=reports,
        )
