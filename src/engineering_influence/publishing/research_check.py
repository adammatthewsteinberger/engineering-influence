# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Research apparatus: required files and a floor on cited source URLs."""

from pathlib import Path
from typing import Any

from engineering_influence.publishing.path_relativizer import PathRelativizer
from engineering_influence.publishing.readiness_report import ReadinessReport
from engineering_influence.publishing.text_statistics import TextStatistics


class ResearchCheck:
    """Counts words and URLs in the configured research files."""

    def run(
        self,
        report: ReadinessReport,
        source: Path,
        release: dict[str, Any],
        severity: str,
        relativizer: PathRelativizer,
    ) -> None:
        """Add findings and record research size."""
        stats = TextStatistics()
        words = urls = 0
        missing: list[str] = []
        for name in (str(item) for item in release.get("required_research_files", [])):
            path = source / name
            if not path.exists():
                missing.append(name)
                continue
            text = path.read_text(encoding="utf-8")
            words += stats.words(text)
            urls += stats.urls(text)
        for name in missing:
            report.add(
                severity,
                "missing-research-file",
                f"required research file does not exist: {name}",
                relativizer.relative(source / name),
            )
        minimum = int(release.get("minimum_source_urls", 0))
        if urls < minimum:
            report.add(
                severity,
                "research-url-floor",
                f"required research files contain {urls} URLs; minimum is {minimum}",
                relativizer.relative(source),
            )
        report.counts["research_words"] = words
        report.counts["research_urls"] = urls
