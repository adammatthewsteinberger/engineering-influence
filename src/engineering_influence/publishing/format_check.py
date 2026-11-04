"""Format policy: KDP hardcover page limit or an explicit external provider."""

from typing import Any

from engineering_influence.publishing.readiness_report import ReadinessReport


class FormatCheck:
    """Rejects a KDP hardcover that is too long or an unprovided external hardcover."""

    def run(
        self,
        report: ReadinessReport,
        release: dict[str, Any],
        severity: str,
        ref: str,
        pdf_ref: str | None,
        hardcover_price: float | None,
    ) -> None:
        """Add findings and record the format decisions."""
        formats = release.get("formats", {})
        if not isinstance(formats, dict):
            report.add(severity, "format-contract", "[release.formats] must be a table", ref)
            formats = {}
        limit = int(formats.get("kdp_hardcover_max_pages", 550))
        kdp_hardcover = bool(formats.get("kdp_hardcover", False))
        provider = str(formats.get("hardcover_provider", "")).strip()
        pages = report.page_count
        if kdp_hardcover and pages is not None and pages > limit:
            report.add(
                severity,
                "hardcover-page-limit",
                f"KDP hardcover would have {pages} pages; configured maximum is {limit}",
                pdf_ref,
            )
        elif not kdp_hardcover and hardcover_price is not None:
            if not provider:
                report.add(
                    severity,
                    "hardcover-provider-missing",
                    "non-KDP hardcover requires an explicit provider",
                    ref,
                )
            else:
                report.add(
                    "warning",
                    "external-hardcover",
                    f"hardcover price is configured for external provider: {provider}",
                    ref,
                )
        report.formats = {
            "kdp_hardcover": kdp_hardcover,
            "kdp_hardcover_max_pages": limit,
            "hardcover_provider": provider or None,
            "page_count": pages,
        }
