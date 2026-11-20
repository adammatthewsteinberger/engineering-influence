# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Audits publication metadata, research apparatus, pricing, and format policy."""

import tomllib
from datetime import date
from pathlib import Path

from engineering_influence.interfaces.manuscript_source_interface import ManuscriptSourceInterface
from engineering_influence.interfaces.pdf_inspector_interface import PdfInspectorInterface
from engineering_influence.models.publishing.path_relativizer import PathRelativizer
from engineering_influence.models.publishing.release_readiness_report import ReleaseReadinessReport
from engineering_influence.services.publishing.format_check import FormatCheck
from engineering_influence.services.publishing.metadata_check import MetadataCheck
from engineering_influence.services.publishing.pricing_check import PricingCheck
from engineering_influence.services.publishing.research_check import ResearchCheck


class ReleaseAuditor:
    """Proves a release has the decisions that used to live in chat or memory."""

    def __init__(
        self,
        root: Path,
        files: ManuscriptSourceInterface,
        pdfs: PdfInspectorInterface,
        today: date | None = None,
    ) -> None:
        self._root = root
        self._files = files
        self._pdfs = pdfs
        self._relativizer = PathRelativizer(root)
        self._today = today

    def audit(
        self, config_path: Path, *, pdf: Path | None = None, strict: bool = False
    ) -> ReleaseReadinessReport:
        """Return the readiness report for one book config."""
        config = tomllib.loads(self._files.read_text(config_path))
        ref = self._relativizer.relative(config_path)
        pages = self._pdfs.page_count(pdf) if pdf is not None else None
        report = ReleaseReadinessReport(1, config_path.stem, "pass", ref, pages)
        release = config.get("release")
        if not isinstance(release, dict):
            report.add(
                "error" if strict else "warning",
                "missing-release-contract",
                "book config has no [release] contract",
                ref,
            )
            report.status = "fail" if report.errors else "warning"
            return report
        severity = "error" if (strict or bool(release.get("required", False))) else "warning"
        MetadataCheck().run(report, config, release, severity, ref)
        ResearchCheck(self._files).run(
            report, self._root / config["source"], release, severity, self._relativizer
        )
        pricing_check = PricingCheck(self._today)
        pricing, ebook, paperback, hardcover = pricing_check.validate(
            report, release, severity, ref
        )
        pdf_ref = self._relativizer.relative(pdf) if pdf is not None else None
        FormatCheck().run(report, release, severity, ref, pdf_ref, hardcover)
        pricing_check.estimate(report, pricing, (ebook, paperback, hardcover), pages)
        report.status = "fail" if report.errors else "warning" if report.warnings else "pass"
        return report
