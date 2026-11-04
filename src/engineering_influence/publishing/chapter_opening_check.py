# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Chapter openings: a stable drop cap, and no lowercase paragraph fragments."""

import re
from pathlib import Path
from typing import Any

from engineering_influence.publishing.issue_recorder import IssueRecorder
from engineering_influence.publishing.manuscript_text import ManuscriptText


class ChapterOpeningCheck:
    """A lowercase first paragraph breaks the print initial; later ones are fragments."""

    def run(
        self,
        recorder: IssueRecorder,
        path: Path,
        text: str,
        body: str,
        quality: dict[str, Any],
    ) -> None:
        """Record opening and paragraph-start issues for one chapter."""
        paragraphs = ManuscriptText().paragraphs(body)
        first = paragraphs[0] if paragraphs else ""
        if not first:
            recorder.record("error", "missing-opening", "chapter has no prose opening", path)
        elif first[0].isalpha() and not first[0].isupper():
            recorder.record(
                "error",
                "opening-not-capitalized",
                "chapter opening must begin with an uppercase letter so the print drop cap is stable",
                path,
            )
        # Later lowercase starts can be deliberate rhetorical fragments, so they stay editorial
        # warnings unless a book opts into the stricter gate.
        severity = "error" if quality.get("fail_on_lowercase_paragraphs", False) else "warning"
        # Some names are lowercase by convention; a book lists them in allowed_lowercase_starts.
        allowed = tuple(str(item) for item in quality.get("allowed_lowercase_starts", ()))
        allowed_pattern = "(?:" + "|".join(map(re.escape, allowed)) + r")\b" if allowed else None
        for paragraph in paragraphs[1:]:
            if allowed_pattern and re.match(allowed_pattern, paragraph.lstrip()):
                continue
            initial = paragraph.lstrip()[:1]
            if initial.isalpha() and initial.islower():
                recorder.record(
                    severity,
                    "paragraph-start-lowercase",
                    "reader-facing paragraph begins with a lowercase letter",
                    path,
                    text,
                    text.find(paragraph),
                )
