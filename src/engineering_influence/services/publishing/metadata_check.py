# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Release metadata: title, subtitle, author, description, keywords."""

from typing import Any

from engineering_influence.models.publishing.release_readiness_report import ReleaseReadinessReport
from engineering_influence.services.publishing.interfaces.metadata_check_interface import (
    MetadataCheckInterface,
)
from engineering_influence.services.publishing.text_statistics import TextStatistics


class MetadataCheck(MetadataCheckInterface):
    """Requires complete listing metadata, a description within KDP's limits, seven unique keywords.

    KDP accepts a description of up to 4,000 characters; ``release.maximum_description_characters``
    lowers that limit for a book that wants a shorter listing.
    """

    DESCRIPTION_LIMIT = 4000

    def run(
        self,
        report: ReleaseReadinessReport,
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
        characters = len(description)
        maximum = int(release.get("maximum_description_characters", self.DESCRIPTION_LIMIT))
        if characters > maximum:
            report.add(
                severity,
                "description-too-long",
                f"description has {characters} characters; KDP allows {maximum}",
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
        report.counts["description_characters"] = characters
        report.metadata = {
            "title": title,
            "subtitle": subtitle,
            "author": author,
            "keywords": keywords,
        }
