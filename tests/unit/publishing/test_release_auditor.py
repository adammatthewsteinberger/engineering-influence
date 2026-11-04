"""Release-readiness behavior over small temporary books."""

import copy
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfWriter

from engineering_influence.publishing.readiness_report import ReadinessReport
from engineering_influence.publishing.release_auditor import ReleaseAuditor

TODAY = date(2026, 11, 4)
Dump = Callable[[dict[str, Any]], str]

VALID: dict[str, Any] = {
    "source": "src",
    "title": "Title",
    "subtitle": "Subtitle",
    "author": "Author",
    "description": "word " * 90,
    "release": {
        "keywords": ["a", "b", "c", "d", "e", "f", "g"],
        "required_research_files": ["research.md"],
        "minimum_source_urls": 2,
        "pricing": {
            "verified_on": "2026-10-20",
            "source_url": "https://example.com/pricing",
            "ebook": 5.99,
            "paperback": 14.99,
            "hardcover": 24.99,
        },
        "formats": {"kdp_hardcover": False, "hardcover_provider": "IngramSpark"},
    },
}


def audit(
    root: Path,
    dump: Dump,
    mutate: Callable[[dict[str, Any]], None] | None = None,
    *,
    pages: int | None = 100,
    strict: bool = False,
) -> ReadinessReport:
    config = copy.deepcopy(VALID)
    if mutate:
        mutate(config)
    source = root / "src"
    source.mkdir(exist_ok=True)
    (source / "research.md").write_text("See https://a.example and https://b.example.", "utf-8")
    pdf = root / "book.pdf"
    if pages is not None:
        writer = PdfWriter()
        for _ in range(pages):
            writer.add_blank_page(432, 648)
        with pdf.open("wb") as handle:
            writer.write(handle)
    path = root / "demo.toml"
    path.write_text(dump(config), encoding="utf-8")
    return ReleaseAuditor(root, TODAY).audit(path, pdf=pdf, strict=strict)


def codes(report: ReadinessReport) -> list[str]:
    return [finding.code for finding in report.findings]


def test_valid_contract_estimates_cost_and_royalties(tmp_path: Path, dump: Dump) -> None:
    report = audit(tmp_path, dump)
    assert codes(report) == ["external-hardcover"] and report.status == "warning"
    assert report.pricing["estimated_paperback_print_cost"] == 2.2
    assert report.pricing["estimated_paperback_royalty"] == 6.79
    assert report.pricing["estimated_ebook_royalty"] == 4.04
    assert report.pricing["verified_age_days"] == 15
    assert report.formats["hardcover_provider"] == "IngramSpark"
    assert report.counts["research_urls"] == 2 and report.metadata["title"] == "Title"
    assert report.as_dict()["slug"] == "demo" and report.errors == []


def test_clean_pass_with_a_kdp_hardcover_inside_the_limit(tmp_path: Path, dump: Dump) -> None:
    def change(config: dict[str, Any]) -> None:
        config["release"]["formats"] = {"kdp_hardcover": True}

    report = audit(tmp_path, dump, change)
    assert report.status == "pass" and report.findings == []


def test_missing_hardcover_price_is_a_finding(tmp_path: Path, dump: Dump) -> None:
    def change(config: dict[str, Any]) -> None:
        del config["release"]["pricing"]["hardcover"]

    assert codes(audit(tmp_path, dump, change)) == ["hardcover-price-missing"]


@pytest.mark.parametrize(
    ("strict", "status", "severity"), [(True, "fail", "error"), (False, "warning", "warning")]
)
def test_missing_release_contract(
    tmp_path: Path, dump: Dump, strict: bool, status: str, severity: str
) -> None:
    def change(config: dict[str, Any]) -> None:
        del config["release"]

    report = audit(tmp_path, dump, change, strict=strict)
    assert (report.status, report.findings[0].severity) == (status, severity)
    assert report.findings[0].code == "missing-release-contract"


def test_required_release_promotes_warnings_to_errors(tmp_path: Path, dump: Dump) -> None:
    def change(config: dict[str, Any]) -> None:
        config["release"]["required"] = True
        config["title"] = ""

    report = audit(tmp_path, dump, change)
    assert report.status == "fail" and "missing-title" in codes(report)
    assert report.findings[0].severity == "error"


def test_metadata_defects(tmp_path: Path, dump: Dump) -> None:
    def change(config: dict[str, Any]) -> None:
        config.update(title="", subtitle="", author="", description="too short")
        config["release"]["keywords"] = ["a", "", "a", "b", "c", "d", "e"]

    assert codes(audit(tmp_path, dump, change)) == [
        "missing-title",
        "missing-subtitle",
        "missing-author",
        "description-too-short",
        "empty-keyword",
        "duplicate-keyword",
        "external-hardcover",
    ]


def test_keyword_count_must_be_seven(tmp_path: Path, dump: Dump) -> None:
    def change(config: dict[str, Any]) -> None:
        config["release"]["keywords"] = ["only"]

    assert "keyword-count" in codes(audit(tmp_path, dump, change))


def test_research_files_and_url_floor(tmp_path: Path, dump: Dump) -> None:
    def change(config: dict[str, Any]) -> None:
        config["release"]["required_research_files"] = ["research.md", "absent.md"]
        config["release"]["minimum_source_urls"] = 5

    report = audit(tmp_path, dump, change)
    assert codes(report)[:2] == ["missing-research-file", "research-url-floor"]
    assert report.findings[0].path == "src/absent.md"


@pytest.mark.parametrize(
    ("pricing", "expected"),
    [
        ({"verified_on": "", "source_url": "x"}, ["pricing-not-dated", "pricing-source-missing"]),
        ({"verified_on": "2026-01-01"}, ["pricing-stale"]),
        ({"verified_on": "not a date"}, ["pricing-date-invalid"]),
        ({"max_verification_age_days": "soon"}, ["pricing-date-invalid"]),
        ({"ebook": "free"}, ["ebook-price-missing"]),
        ({"ebook": 1.0}, ["ebook-price-range"]),
        ({"paperback": 8.0}, ["paperback-price-tier"]),
        ({"paperback": 7.0}, ["paperback-price-tier", "ebook-print-price-gap"]),
    ],
)
def test_pricing_defects(
    tmp_path: Path, dump: Dump, pricing: dict[str, Any], expected: list[str]
) -> None:
    def change(config: dict[str, Any]) -> None:
        config["release"]["pricing"].update(pricing)

    found = [code for code in codes(audit(tmp_path, dump, change)) if code != "external-hardcover"]
    assert found == expected


def test_pricing_must_be_a_table(tmp_path: Path, dump: Dump) -> None:
    def change(config: dict[str, Any]) -> None:
        config["release"]["pricing"] = 5

    found = codes(audit(tmp_path, dump, change))
    assert found[0] == "missing-pricing" and "pricing-not-dated" in found
    assert "ebook-price-missing" in found


def test_formats_must_be_a_table(tmp_path: Path, dump: Dump) -> None:
    def change(config: dict[str, Any]) -> None:
        config["release"]["formats"] = "kdp"

    assert "format-contract" in codes(audit(tmp_path, dump, change))


def test_kdp_hardcover_page_limit(tmp_path: Path, dump: Dump) -> None:
    def change(config: dict[str, Any]) -> None:
        config["release"]["formats"] = {"kdp_hardcover": True, "kdp_hardcover_max_pages": 50}

    report = audit(tmp_path, dump, change)
    finding = next(f for f in report.findings if f.code == "hardcover-page-limit")
    assert finding.path == "book.pdf" and "100 pages" in finding.message
    assert [f.code for f in audit(tmp_path, dump, change, pages=10).findings] == []


def test_external_hardcover_needs_a_provider(tmp_path: Path, dump: Dump) -> None:
    def change(config: dict[str, Any]) -> None:
        config["release"]["formats"] = {"kdp_hardcover": False}

    assert "hardcover-provider-missing" in codes(audit(tmp_path, dump, change))


def test_missing_pdf_means_no_page_count_or_estimate(tmp_path: Path, dump: Dump) -> None:
    report = audit(tmp_path, dump, pages=None)
    assert report.page_count is None
    assert report.pricing["estimated_paperback_print_cost"] is None
    assert report.pricing["estimated_paperback_royalty"] is None


def test_no_pdf_argument_and_no_ebook_price(tmp_path: Path, dump: Dump) -> None:
    def change(config: dict[str, Any]) -> None:
        del config["release"]["pricing"]["ebook"]

    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "research.md").write_text("https://a.example https://b.example", "utf-8")
    config = copy.deepcopy(VALID)
    change(config)
    path = tmp_path / "demo.toml"
    path.write_text(dump(config), encoding="utf-8")
    report = ReleaseAuditor(tmp_path, TODAY).audit(path)
    assert "ebook-price-missing" in codes(report)
    assert report.pricing["estimated_ebook_royalty"] is None
    assert report.formats["page_count"] is None


def test_default_today_is_used_when_not_injected(tmp_path: Path, dump: Dump) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "research.md").write_text("x", "utf-8")
    path = tmp_path / "demo.toml"
    path.write_text(dump(VALID), encoding="utf-8")
    report = ReleaseAuditor(tmp_path).audit(path)
    assert isinstance(report.pricing["verified_age_days"], int)
