# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Repeated rhetorical formulas across the printed manuscript."""

import re
from pathlib import Path
from typing import Any

from engineering_influence.publishing.audit_defaults import AuditDefaults
from engineering_influence.publishing.audit_report import AuditReport
from engineering_influence.publishing.issue_recorder import IssueRecorder


class FormulaCheck:
    """Warns when a formula such as 'the question is not' is overused."""

    def run(
        self,
        report: AuditReport,
        recorder: IssueRecorder,
        quality: dict[str, Any],
        source: Path,
    ) -> None:
        """Count each formula and warn above the threshold."""
        threshold = int(quality.get("formula_warning_threshold", 4))
        texts = [
            (source / entry.file).read_text(encoding="utf-8")
            for entry in report.entries
            if (source / entry.file).exists()
        ]
        for phrase in quality.get("formula_phrases", AuditDefaults.FORMULA_PHRASES):
            pattern = re.escape(str(phrase))
            count = sum(len(re.findall(pattern, text, flags=re.IGNORECASE)) for text in texts)
            report.style_formula_counts[str(phrase)] = count
            if count > threshold:
                recorder.record(
                    "warning",
                    "repeated-rhetorical-formula",
                    f"{phrase!r} appears {count} times; threshold is {threshold}",
                )
