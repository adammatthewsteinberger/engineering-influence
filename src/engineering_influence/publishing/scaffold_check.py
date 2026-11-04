# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reader-facing scaffolding: forbidden paragraph starts and planning phrases."""

import re
from pathlib import Path
from typing import Any

from engineering_influence.publishing.audit_defaults import AuditDefaults
from engineering_influence.publishing.issue_recorder import IssueRecorder
from engineering_influence.publishing.manuscript_text import ManuscriptText


class ScaffoldCheck:
    """Planning or proof language that leaked into the printed copy."""

    def run(
        self,
        recorder: IssueRecorder,
        path: Path,
        text: str,
        body: str,
        quality: dict[str, Any],
    ) -> None:
        """Record every configured forbidden start and phrase found."""
        for start in tuple(quality.get("forbidden_paragraph_starts", ())):
            for paragraph in ManuscriptText().paragraphs(body):
                if paragraph.lstrip().lower().startswith(str(start).lower()):
                    recorder.record(
                        "error",
                        "forbidden-paragraph-start",
                        f"paragraph starts with configured fragment {start!r}",
                        path,
                        text,
                        text.find(paragraph),
                    )
        for phrase in quality.get("forbidden_phrases", AuditDefaults.FORBIDDEN_PHRASES):
            match = re.search(re.escape(str(phrase)), text, flags=re.IGNORECASE)
            if match:
                recorder.record(
                    "error",
                    "reader-facing-scaffold",
                    f"configured planning/proof phrase appears in reader-facing copy: {phrase!r}",
                    path,
                    text,
                    match.start(),
                )
