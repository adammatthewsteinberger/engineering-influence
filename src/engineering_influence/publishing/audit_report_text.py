# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Human-readable renderings of the audit reports."""

from engineering_influence.publishing.audit_report import AuditReport
from engineering_influence.publishing.readiness_report import ReadinessReport


class AuditReportText:
    """The lines a person reads after an audit."""

    def manuscript(self, report: AuditReport) -> str:
        """Counts, every issue and warning with its location, and a pass line."""
        lines = [
            (
                f"[{report.slug}] {report.counts.get('listed_words', 0):,} listed words, "
                f"{report.counts.get('chapter_count', 0)} chapters, "
                f"{report.counts.get('back_count', 0)} back-matter entries"
            )
        ]
        for issue in report.issues + report.warnings:
            if issue.path and issue.line:
                location = f" {issue.path}:{issue.line}"
            elif issue.path:
                location = f" {issue.path}"
            else:
                location = ""
            lines.append(f"{issue.severity.upper()} [{issue.code}]{location}: {issue.message}")
        if not report.issues:
            suffix = f", {len(report.warnings)} warning(s)" if report.warnings else ""
            lines.append(f"[{report.slug}] manuscript audit passed{suffix}")
        return "\n".join(lines)

    def release(self, report: ReadinessReport) -> str:
        """Release-readiness status and each finding."""
        lines = [
            (
                f"[{report.slug}] release readiness {report.status}; "
                f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)"
            )
        ]
        for finding in report.findings:
            location = f" ({finding.path})" if finding.path else ""
            lines.append(f"{finding.severity.upper()} [{finding.code}] {finding.message}{location}")
        return "\n".join(lines)
