# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writes quality-report.json: what the run recorded, what the build found, and the hash of every finished file."""

import hashlib
import json

from engineering_influence.models.manuscript_build import ManuscriptBuild
from engineering_influence.models.quality_issue import QualityIssue
from engineering_influence.services.interfaces.quality_report_interface import (
    QualityReportInterface,
)


class QualityReport(QualityReportInterface):
    """The same inputs give the same bytes: keys are sorted, and nothing in it depends on the clock.

    ``issues`` are the ones the run recorded along the way (a bounded loop that ran out, a continuity
    finding); ``errors`` and ``warnings`` are the build's. ``files`` lists the book's finished files, each with
    its size and SHA-256, so a person can check what was built against what was packaged.
    """

    def render(self, slug: str, issues: tuple[QualityIssue, ...], build: ManuscriptBuild) -> bytes:
        """The report as JSON, ending in a newline."""
        document = {
            "schema_version": 1,
            "slug": slug,
            "status": "pass" if build.passed else "fail",
            "issues": [
                {
                    "stage": issue.stage,
                    "code": issue.code,
                    "detail": issue.detail,
                    "blocking": issue.blocking,
                }
                for issue in issues
            ],
            "errors": list(build.errors),
            "warnings": list(build.warnings),
            "steps": [{"name": name, "status": status} for name, status in build.steps],
            "files": [
                {
                    "path": f"book/{name}",
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }
                for name, data in build.book
            ],
        }
        return (json.dumps(document, indent=2, sort_keys=True) + "\n").encode("utf-8")
