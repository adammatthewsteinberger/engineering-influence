"""Records located issues on an audit report."""

from pathlib import Path

from engineering_influence.publishing.audit_report import AuditReport
from engineering_influence.publishing.issue import Issue
from engineering_influence.publishing.path_relativizer import PathRelativizer


class IssueRecorder:
    """Turns a path and a text offset into a root-relative path and a line number."""

    def __init__(self, report: AuditReport, relativizer: PathRelativizer) -> None:
        self._report = report
        self._relativizer = relativizer

    def record(
        self,
        severity: str,
        code: str,
        message: str,
        path: Path | None = None,
        text: str | None = None,
        offset: int | None = None,
    ) -> None:
        """Add an issue, computing its 1-based line when text and offset are given."""
        line = text[:offset].count("\n") + 1 if text is not None and offset is not None else None
        location = self._relativizer.relative(path) if path else None
        self._report.add(Issue(severity, code, message, location, line))
