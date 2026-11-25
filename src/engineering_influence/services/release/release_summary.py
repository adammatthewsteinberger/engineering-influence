# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The release-readiness section of a publication report."""

from dataclasses import asdict
from typing import Any

from engineering_influence.models.publishing.release_readiness_report import ReleaseReadinessReport
from engineering_influence.services.release.interfaces.release_summary_interface import (
    ReleaseSummaryInterface,
)


class ReleaseSummary(ReleaseSummaryInterface):
    """Status, findings, pricing, and format decisions, with the path of the full report."""

    def of(self, report: ReleaseReadinessReport, report_path: str) -> dict[str, Any]:
        """The summary dictionary for a release-readiness report."""
        return {
            "status": report.status,
            "report": report_path,
            "findings": [asdict(finding) for finding in report.findings],
            "pricing": report.pricing,
            "formats": report.formats,
        }
