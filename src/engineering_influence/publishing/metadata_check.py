# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Release metadata: title, subtitle, author, description, keywords."""

from typing import Any

from engineering_influence.publishing.readiness_report import ReadinessReport
from engineering_influence.publishing.text_statistics import TextStatistics


class MetadataCheck:
    """Requires complete listing metadata and exactly seven unique keywords."""

    def run(
        self,
        report: ReadinessReport,
        config: dict[str, Any],
        release: dict[str, Any],
        severity: str,
        ref: str,
    ) -> None:
        """Add findings and record description size and the metadata block."""
        title = str(config.get("title", "")).strip()
        subtitle = str(config.get("subtitle", "")).strip()
        author = str(config.get("author", "")).strip()
        description = str(config.get("description", "")).strip()
        keywords = release.get("keywords", [])
        for value, code, label in (
            (title, "missing-title", "title"),
            (subtitle, "missing-subtitle", "subtitle"),
            (author, "missing-author", "author"),
        ):
            if not value:
                report.add(severity, code, f"top-level {label} is empty", ref)
        minimum = int(release.get("minimum_description_words", 80))
        words = TextStatistics().words(description)
        if words < minimum:
            report.add(
                severity,
                "description-too-short",
                f"description has {words} words; minimum is {minimum}",
                ref,
            )
        if not isinstance(keywords, list) or len(keywords) != 7:
            report.add(
                severity,
                "keyword-count",
                "release contract must contain exactly seven keywords",
                ref,
            )
        else:
            normalised = [str(keyword).strip().casefold() for keyword in keywords]
            if any(not keyword for keyword in normalised):
                report.add(severity, "empty-keyword", "keywords may not be empty", ref)
            if len(set(normalised)) != len(normalised):
                report.add(severity, "duplicate-keyword", "keywords must be unique", ref)
        report.counts["description_words"] = words
        report.metadata = {
            "title": title,
            "subtitle": subtitle,
            "author": author,
            "keywords": keywords,
        }
