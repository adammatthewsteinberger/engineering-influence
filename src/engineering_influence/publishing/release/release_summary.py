# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The release-readiness section of a publication report."""

from dataclasses import asdict
from typing import Any

from engineering_influence.publishing.readiness_report import ReadinessReport


class ReleaseSummary:
    """Status, findings, pricing, and format decisions, with the path of the full report."""

    def of(self, report: ReadinessReport, report_path: str) -> dict[str, Any]:
        """The summary dictionary for a release-readiness report."""
        return {
            "status": report.status,
            "report": report_path,
            "findings": [asdict(finding) for finding in report.findings],
            "pricing": report.pricing,
            "formats": report.formats,
        }
