# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pricing inputs: freshness, source, list-price policy, and royalty estimates."""

from datetime import date
from typing import Any

from engineering_influence.publishing.readiness_report import ReadinessReport
from engineering_influence.publishing.text_statistics import TextStatistics


class PricingCheck:
    """Validates volatile pricing assumptions and records the inputs used."""

    def __init__(self, today: date | None = None) -> None:
        self._today = today or date.today()

    def validate(
        self, report: ReadinessReport, release: dict[str, Any], severity: str, ref: str
    ) -> tuple[dict[str, Any], float | None, float | None, float | None]:
        """Return (pricing table, ebook, paperback, hardcover list prices)."""
        pricing = release.get("pricing", {})
        if not isinstance(pricing, dict):
            report.add(severity, "missing-pricing", "[release.pricing] must be a table", ref)
            pricing = {}
        verified_on = str(pricing.get("verified_on", ""))
        if not verified_on:
            report.add(
                severity, "pricing-not-dated", "pricing inputs must include verified_on", ref
            )
        else:
            try:
                age = (self._today - date.fromisoformat(verified_on)).days
                report.pricing["verified_age_days"] = age
                if age > int(pricing.get("max_verification_age_days", 90)):
                    report.add(severity, "pricing-stale", f"pricing inputs are {age} days old", ref)
            except ValueError:
                report.add(
                    severity,
                    "pricing-date-invalid",
                    f"pricing verified_on is not ISO date: {verified_on!r}",
                    ref,
                )
        if not TextStatistics().is_url(str(pricing.get("source_url", ""))):
            report.add(
                severity, "pricing-source-missing", "pricing inputs must name a source URL", ref
            )
        ebook = self._price(report, pricing, "ebook", severity, ref)
        paperback = self._price(report, pricing, "paperback", severity, ref)
        hardcover = self._price(report, pricing, "hardcover", severity, ref)
        if ebook is not None and not 2.99 <= ebook <= 12.99:
            report.add(
                severity,
                "ebook-price-range",
                f"ebook price ${ebook:.2f} is outside the 70% royalty range",
                ref,
            )
        if paperback is not None and paperback < 9.99:
            report.add(
                severity,
                "paperback-price-tier",
                f"paperback price ${paperback:.2f} misses the 60% Amazon.com tier",
                ref,
            )
        if ebook is not None and paperback is not None and ebook > paperback * 0.8 + 1e-9:
            report.add(
                severity,
                "ebook-print-price-gap",
                "ebook must be at least 20% below paperback for the declared KDP strategy",
                ref,
            )
        return pricing, ebook, paperback, hardcover

    def estimate(
        self,
        report: ReadinessReport,
        pricing: dict[str, Any],
        prices: tuple[float | None, float | None, float | None],
        page_count: int | None,
    ) -> None:
        """Record list prices, assumptions, and estimated print cost and royalties."""
        ebook, paperback, hardcover = prices
        fixed = float(pricing.get("paperback_fixed_cost", 1.00))
        per_page = float(pricing.get("paperback_per_page_cost", 0.012))
        ebook_rate = float(pricing.get("ebook_royalty_rate", 0.70))
        paperback_rate = float(pricing.get("paperback_royalty_rate", 0.60))
        delivery = float(pricing.get("ebook_delivery_cost", 0.15))
        cost = fixed + page_count * per_page if page_count is not None else None
        report.pricing.update(
            {
                "currency": pricing.get("currency", "USD"),
                "source_url": str(pricing.get("source_url", "")),
                "verified_on": str(pricing.get("verified_on", "")),
                "list_prices": {"ebook": ebook, "paperback": paperback, "hardcover": hardcover},
                "page_count": page_count,
                "estimated_paperback_print_cost": round(cost, 2) if cost is not None else None,
                "estimated_ebook_royalty": (
                    round(ebook * ebook_rate - delivery, 2) if ebook is not None else None
                ),
                "estimated_paperback_royalty": (
                    round(paperback * paperback_rate - cost, 2)
                    if paperback is not None and cost is not None
                    else None
                ),
                "assumptions": {
                    "paperback_fixed_cost": fixed,
                    "paperback_per_page_cost": per_page,
                    "ebook_delivery_cost": delivery,
                    "ebook_royalty_rate": ebook_rate,
                    "paperback_royalty_rate": paperback_rate,
                },
            }
        )

    def _price(
        self, report: ReadinessReport, pricing: dict[str, Any], name: str, severity: str, ref: str
    ) -> float | None:
        try:
            return float(pricing.get(name))  # type: ignore[arg-type]
        except (TypeError, ValueError):
            report.add(
                severity, f"{name}-price-missing", f"pricing must define {name} as a number", ref
            )
            return None
