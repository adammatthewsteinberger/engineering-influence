# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Audits a book by laying its files out as a project in a scratch folder and running the pipeline on it."""

import tempfile
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

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
            for name, data in files.items():
                target = (root / name).resolve()
                if not target.is_relative_to(root) or target == root:
                    raise ValueError(f"the file {name!r} would leave the project")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
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
            errors=self._errors(result),
            warnings=self._warnings(result),
            files=reports,
        )

    @staticmethod
    def _errors(result: dict[str, Any]) -> tuple[str, ...]:
        audit = result["manuscript_audit"]
        found = [f"{issue['code']}: {issue['message']}" for issue in audit["issues"]]
        found += [
            f"{finding['code']}: {finding['message']}"
            for finding in result["release_readiness"]["findings"]
            if finding["severity"] == "error"
        ]
        return tuple(found)

    @staticmethod
    def _warnings(result: dict[str, Any]) -> tuple[str, ...]:
        audit = result["manuscript_audit"]
        found = [f"{issue['code']}: {issue['message']}" for issue in audit["warnings"]]
        found += [
            f"{finding['code']}: {finding['message']}"
            for finding in result["release_readiness"]["findings"]
            if finding["severity"] != "error"
        ]
        return tuple(found)
