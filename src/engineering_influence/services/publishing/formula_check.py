# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Repeated rhetorical formulas across the printed manuscript."""

import re
from pathlib import Path
from typing import Any

from engineering_influence.interfaces.manuscript_source_interface import ManuscriptSourceInterface
from engineering_influence.models.publishing.audit_report import AuditReport
from engineering_influence.services.publishing.audit_defaults import AuditDefaults
from engineering_influence.services.publishing.interfaces.formula_check_interface import (
    FormulaCheckInterface,
)
from engineering_influence.services.publishing.issue_recorder import IssueRecorder


class FormulaCheck(FormulaCheckInterface):
    """Warns when a formula such as 'the question is not' is overused."""

    def __init__(self, files: ManuscriptSourceInterface) -> None:
        """Remember the source files the formula check reads."""
        self._files = files

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
            self._files.read_text(source / entry.file)
            for entry in report.entries
            if self._files.exists(source / entry.file)
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
