"""Configured depth thresholds: word counts, chapter balance, required back matter."""

from pathlib import Path
from typing import Any

from engineering_influence.publishing.audit_report import AuditReport
from engineering_influence.publishing.issue_recorder import IssueRecorder
from engineering_influence.publishing.manuscript_text import ManuscriptText


class ThresholdCheck:
    """Records counts and thresholds, then reports the ones the manuscript misses."""

    def run(
        self,
        report: AuditReport,
        recorder: IssueRecorder,
        quality: dict[str, Any],
        source: Path,
        source_count: int,
        ignored_count: int,
    ) -> None:
        """Fill report counts and thresholds and record threshold issues."""
        chapters = [entry for entry in report.entries if entry.kind == "chapter"]
        front = [entry for entry in report.entries if entry.kind == "front"]
        back = [entry for entry in report.entries if entry.kind == "back"]
        listed_words = sum(entry.words for entry in report.entries)
        minimum_chapter = int(quality.get("minimum_chapter_words", 0))
        minimum = int(quality.get("minimum_word_count", 0))
        target = int(quality.get("word_count_target", 0))
        expected = int(quality.get("expected_chapter_count", 0))
        max_ratio = float(quality.get("max_chapter_words_ratio", 0))
        fail_on_target = bool(quality.get("fail_on_word_count_target", False))
        report.counts = {
            "listed_words": listed_words,
            "chapter_words": sum(entry.words for entry in chapters),
            "front_words": sum(entry.words for entry in front),
            "back_words": sum(entry.words for entry in back),
            "chapter_count": len(chapters),
            "front_count": len(front),
            "back_count": len(back),
            "source_file_count": source_count,
            "ignored_file_count": ignored_count,
        }
        report.thresholds = {
            "word_count_target": target,
            "minimum_word_count": minimum,
            "minimum_chapter_words": minimum_chapter,
            "expected_chapter_count": expected,
            "max_chapter_words_ratio": max_ratio,
            "fail_on_word_count_target": fail_on_target,
        }
        if expected and len(chapters) != expected:
            recorder.record(
                "error", "chapter-count", f"expected {expected} chapters, found {len(chapters)}"
            )
        if minimum and listed_words < minimum:
            recorder.record(
                "error",
                "word-count-floor",
                f"listed manuscript has {listed_words:,} words; minimum is {minimum:,}",
            )
        if target and listed_words < target:
            recorder.record(
                "error" if fail_on_target else "warning",
                "word-count-target",
                f"listed manuscript has {listed_words:,} words; target is {target:,}",
            )
        for entry in chapters:
            if minimum_chapter and entry.words < minimum_chapter:
                recorder.record(
                    "error",
                    "chapter-word-floor",
                    f"chapter {entry.number} has {entry.words:,} words; "
                    f"minimum is {minimum_chapter:,}",
                    source / entry.file,
                )
        if chapters and max_ratio:
            shortest = min(entry.words for entry in chapters)
            longest = max(entry.words for entry in chapters)
            ratio = longest / shortest if shortest else float("inf")
            report.counts["chapter_words_ratio"] = round(ratio, 3)
            if ratio > max_ratio:
                recorder.record(
                    "error",
                    "chapter-imbalance",
                    f"longest chapter is {ratio:.2f} times the shortest; maximum is {max_ratio:.2f}",
                )
        normaliser = ManuscriptText()
        configured_back = {normaliser.normalise(entry.title) for entry in back}
        for required in quality.get("required_back_titles", ()):
            if normaliser.normalise(str(required)) not in configured_back:
                recorder.record(
                    "error",
                    "missing-back-matter",
                    f"required back matter is not configured: {required!r}",
                )
