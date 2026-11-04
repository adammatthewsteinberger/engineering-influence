"""Audits publication metadata, research apparatus, pricing, and format policy."""

import tomllib
from datetime import date
from pathlib import Path

from pypdf import PdfReader

from engineering_influence.publishing.format_check import FormatCheck
from engineering_influence.publishing.metadata_check import MetadataCheck
from engineering_influence.publishing.path_relativizer import PathRelativizer
from engineering_influence.publishing.pricing_check import PricingCheck
from engineering_influence.publishing.readiness_report import ReadinessReport
from engineering_influence.publishing.research_check import ResearchCheck


class ReleaseAuditor:
    """Proves a release has the decisions that used to live in chat or memory."""

    def __init__(self, root: Path, today: date | None = None) -> None:
        self._root = root
        self._relativizer = PathRelativizer(root)
        self._today = today

    def audit(
        self, config_path: Path, *, pdf: Path | None = None, strict: bool = False
    ) -> ReadinessReport:
        """Return the readiness report for one book config."""
        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        ref = self._relativizer.relative(config_path)
        pages = len(PdfReader(str(pdf)).pages) if pdf is not None and pdf.exists() else None
        report = ReadinessReport(1, config_path.stem, "pass", ref, pages)
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
        ResearchCheck().run(
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
