"""Release-readiness behavior over small temporary books."""

import copy
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from pypdf import PdfWriter

from engineering_influence.infrastructure.publishing.filesystem_manuscript_source import (
    FilesystemManuscriptSource,
)
from engineering_influence.infrastructure.publishing.pypdf_pdf_inspector import PypdfPdfInspector
from engineering_influence.models.publishing.release_readiness_report import ReleaseReadinessReport
from engineering_influence.services.publishing.release_auditor import ReleaseAuditor

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
        "categories": [
            "Books > Literature & Fiction > Genre Fiction > Historical",
            "Books > History > World",
        ],
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
) -> ReleaseReadinessReport:
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
    return ReleaseAuditor(root, FilesystemManuscriptSource(), PypdfPdfInspector(), TODAY).audit(
        path, pdf=pdf, strict=strict
    )


def codes(report: ReleaseReadinessReport) -> list[str]:
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
    report = ReleaseAuditor(
        tmp_path, FilesystemManuscriptSource(), PypdfPdfInspector(), TODAY
    ).audit(path)
    assert "ebook-price-missing" in codes(report)
    assert report.pricing["estimated_ebook_royalty"] is None
    assert report.formats["page_count"] is None


def test_default_today_is_used_when_not_injected(tmp_path: Path, dump: Dump) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "research.md").write_text("x", "utf-8")
    path = tmp_path / "demo.toml"
    path.write_text(dump(VALID), encoding="utf-8")
    report = ReleaseAuditor(tmp_path, FilesystemManuscriptSource(), PypdfPdfInspector()).audit(path)
    assert isinstance(report.pricing["verified_age_days"], int)


def five_by_eight(config: dict[str, Any]) -> None:
    config["trim_size"] = "5x8"
    config["release"]["formats"] = {"kdp_hardcover": False}
    del config["release"]["pricing"]["hardcover"]


def test_a_five_by_eight_paperback_only_book_needs_no_hardcover_price(
    tmp_path: Path, dump: Dump
) -> None:
    report = audit(tmp_path, dump, five_by_eight)
    assert report.status == "pass" and report.findings == []


def test_a_six_by_nine_book_still_needs_its_hardcover_price(tmp_path: Path, dump: Dump) -> None:
    def change(config: dict[str, Any]) -> None:
        config["trim_size"] = "6x9"
        del config["release"]["pricing"]["hardcover"]

    assert codes(audit(tmp_path, dump, change)) == ["hardcover-price-missing"]


def test_a_five_by_eight_book_that_gives_a_hardcover_price_is_still_checked_for_a_provider(
    tmp_path: Path, dump: Dump
) -> None:
    def change(config: dict[str, Any]) -> None:
        five_by_eight(config)
        config["release"]["pricing"]["hardcover"] = 24.99
        config["release"]["formats"] = {"kdp_hardcover": False}

    assert codes(audit(tmp_path, dump, change)) == ["hardcover-provider-missing"]


def test_a_five_by_eight_book_may_not_claim_a_kdp_hardcover(tmp_path: Path, dump: Dump) -> None:
    def change(config: dict[str, Any]) -> None:
        five_by_eight(config)
        config["release"]["formats"] = {"kdp_hardcover": True}

    assert "hardcover-trim-unsupported" in codes(audit(tmp_path, dump, change))


def test_a_five_and_a_half_by_eight_and_a_half_book_may_claim_a_kdp_hardcover(
    tmp_path: Path, dump: Dump
) -> None:
    def change(config: dict[str, Any]) -> None:
        config["trim_size"] = "5.5x8.5"
        config["release"]["formats"] = {"kdp_hardcover": True}

    report = audit(tmp_path, dump, change)
    assert "hardcover-trim-unsupported" not in codes(report)


def clean(*changes: Callable[[dict[str, Any]], None]) -> Callable[[dict[str, Any]], None]:
    """A baseline with nothing to report (a KDP hardcover, so no external-provider warning)."""

    def apply(config: dict[str, Any]) -> None:
        config["release"]["formats"] = {"kdp_hardcover": True}
        for change in changes:
            change(config)

    return apply


def longer_than(limit: int) -> str:
    """Exactly ``limit`` characters of words, ending in a letter so stripping cannot shorten it."""
    text = ("word " * (limit // 5 + 1))[:limit]
    return text[:-1] + "x" if text.endswith(" ") else text


def test_a_description_at_kdps_limit_passes_and_one_character_over_does_not(
    tmp_path: Path, dump: Dump
) -> None:
    def at_limit(config: dict[str, Any]) -> None:
        config["description"] = longer_than(4000)

    def over(config: dict[str, Any]) -> None:
        config["description"] = longer_than(4001)

    assert len(longer_than(4000)) == 4000 and not longer_than(4000).endswith(" ")
    assert audit(tmp_path, dump, clean(at_limit)).findings == []
    report = audit(tmp_path, dump, clean(over))
    assert codes(report) == ["description-too-long"]
    assert report.findings[0].message == "description has 4001 characters; KDP allows 4000"
    assert report.counts["description_characters"] == 4001


def test_a_book_can_set_a_shorter_description_limit(tmp_path: Path, dump: Dump) -> None:
    def change(config: dict[str, Any]) -> None:
        config["description"] = longer_than(1200)
        config["release"]["maximum_description_characters"] = 1000

    assert codes(audit(tmp_path, dump, clean(change))) == ["description-too-long"]


def test_a_description_over_the_limit_is_an_error_in_a_strict_release(
    tmp_path: Path, dump: Dump
) -> None:
    def change(config: dict[str, Any]) -> None:
        config["description"] = longer_than(4500)

    report = audit(tmp_path, dump, clean(change), strict=True)
    assert [f.severity for f in report.findings] == ["error"] and report.status == "fail"


def with_categories(value: Any) -> Callable[[dict[str, Any]], None]:
    def change(config: dict[str, Any]) -> None:
        if value is None:
            del config["release"]["categories"]
        else:
            config["release"]["categories"] = value

    return change


def test_up_to_three_browse_paths_pass_and_are_recorded(tmp_path: Path, dump: Dump) -> None:
    three = [
        "Books > Literature & Fiction > Genre Fiction > Historical",
        "Books > History > World",
        "Books \u203a Science Fiction & Fantasy \u203a Fantasy",
    ]
    report = audit(tmp_path, dump, clean(with_categories(three)))
    assert report.findings == [] and report.status == "pass"
    assert report.metadata["categories"] == three


def test_a_fourth_category_is_too_many(tmp_path: Path, dump: Dump) -> None:
    four = [f"Books > Fiction > Genre {n}" for n in range(4)]
    assert codes(audit(tmp_path, dump, clean(with_categories(four)))) == ["too-many-categories"]


@pytest.mark.parametrize("code", ["FIC009000", "BUS070000", "HIS037000"])
def test_a_bisac_code_is_not_a_browse_category(tmp_path: Path, dump: Dump, code: str) -> None:
    report = audit(tmp_path, dump, clean(with_categories([code])))
    assert codes(report) == ["category-is-bisac"]
    assert "BISAC subject code" in report.findings[0].message


@pytest.mark.parametrize("entry", ["Fiction", "Books >", "  ", "> Fiction", 7])
def test_a_category_that_is_not_a_browse_path_is_refused(
    tmp_path: Path, dump: Dump, entry: Any
) -> None:
    assert codes(audit(tmp_path, dump, clean(with_categories([entry])))) == ["category-not-a-path"]


def test_the_same_category_twice_is_refused_however_it_is_spaced_or_cased(
    tmp_path: Path, dump: Dump
) -> None:
    twice = ["Books > History > World", "books>history  >  WORLD"]
    assert codes(audit(tmp_path, dump, clean(with_categories(twice)))) == ["duplicate-category"]


def test_categories_that_are_not_a_list_are_refused(tmp_path: Path, dump: Dump) -> None:
    assert codes(audit(tmp_path, dump, clean(with_categories("Books > History")))) == [
        "categories-invalid"
    ]


@pytest.mark.parametrize("value", [None, []])
def test_a_book_with_no_categories_gets_a_warning_and_still_passes_a_strict_release(
    tmp_path: Path, dump: Dump, value: Any
) -> None:
    report = audit(tmp_path, dump, clean(with_categories(value)), strict=True)
    assert codes(report) == ["categories-not-declared"]
    assert [f.severity for f in report.findings] == ["warning"]
    assert report.status == "warning" and report.errors == []


def test_category_problems_are_errors_in_a_strict_release(tmp_path: Path, dump: Dump) -> None:
    report = audit(tmp_path, dump, clean(with_categories(["FIC009000"])), strict=True)
    assert [f.severity for f in report.findings] == ["error"] and report.status == "fail"
