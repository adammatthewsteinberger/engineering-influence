"""Manuscript audit behavior over small temporary books."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

from engineering_influence.publishing.audit_report import AuditReport
from engineering_influence.publishing.book_auditor import BookAuditor
from engineering_influence.publishing.config_entries import ConfigEntries

BODY = "The opening is fine.\n\nA second paragraph follows."
Dump = Callable[[dict[str, Any]], str]


def build(root: Path, dump: Dump, files: dict[str, str], config: dict[str, Any]) -> AuditReport:
    source = root / "src"
    source.mkdir(exist_ok=True)
    for name, text in files.items():
        (source / name).write_text(text, encoding="utf-8")
    config = {"source": "src", **config}
    path = root / "demo.toml"
    path.write_text(dump(config), encoding="utf-8")
    return BookAuditor(root).audit(path)


def codes(report: AuditReport) -> list[str]:
    return [issue.code for issue in report.issues + report.warnings]


def chapter(text: str = BODY, title: str = "# Chapter 1: One\n\n") -> str:
    return title + text


def test_clean_book_passes_and_reports_inventory(tmp_path: Path, dump: Dump) -> None:
    report = build(
        tmp_path,
        dump,
        {"a.md": chapter(), "front.md": "# Front\n\nWelcome."},
        {"front": ["front.md"], "parts": [{"chapters": [{"file": "a.md", "style": "verse"}]}]},
    )
    assert report.status == "pass" and report.errors == []
    assert [(e.kind, e.title, e.style, e.number) for e in report.entries] == [
        ("front", "Front", "prose", None),
        ("chapter", "One", "verse", 1),
    ]
    assert report.counts["chapter_count"] == 1 and report.as_dict()["slug"] == "demo"


def test_entry_defects_are_reported_in_order(tmp_path: Path, dump: Dump) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "dir.md").mkdir()
    report = build(
        tmp_path,
        dump,
        {"empty.md": "", "notitle.md": "plain", "blank.md": "# Chapter 2:", "bare.md": "# T"},
        {
            "front": ["empty.md", "notitle.md", "blank.md", "bare.md", "ghost.md", "dir.md"],
            "parts": [{"chapters": ["bare.md"]}],
        },
    )
    assert codes(report) == [
        "missing-title",
        "missing-title",
        "empty-title",
        "empty-entry",
        "empty-entry",
        "missing-source",
        "unreadable-source",
        "duplicate-file",
        "empty-entry",
        "missing-opening",
    ]


def test_chapter_opening_rules(tmp_path: Path, dump: Dump) -> None:
    report = build(
        tmp_path,
        dump,
        {
            "lower.md": chapter("lowercase start.\n\nFine."),
            "quote.md": chapter("“Quoted opening.”"),
            "epi.md": chapter("> an epigraph\n\nProse here."),
            "body.md": chapter(
                "Opening.\n\nlower fragment.\n\nvibey is a name.\n\nOther fragment."
            ),
        },
        {
            "parts": [{"chapters": ["lower.md", "quote.md", "epi.md", "body.md"]}],
            "quality": {"allowed_lowercase_starts": ["vibey"]},
        },
    )
    assert codes(report) == ["opening-not-capitalized", "paragraph-start-lowercase"]
    assert [issue.severity for issue in report.warnings] == ["warning"]
    assert report.warnings[0].line == 5


def test_lowercase_paragraphs_can_be_errors_without_allowances(tmp_path: Path, dump: Dump) -> None:
    report = build(
        tmp_path,
        dump,
        {"a.md": chapter("Opening.\n\nlower one.")},
        {"parts": [{"chapters": ["a.md"]}], "quality": {"fail_on_lowercase_paragraphs": True}},
    )
    assert codes(report) == ["paragraph-start-lowercase"] and report.status == "fail"


def test_scaffold_starts_and_phrases(tmp_path: Path, dump: Dump) -> None:
    report = build(
        tmp_path,
        dump,
        {
            "a.md": chapter("Opening.\n\nIn short, a fragment.\n\nEvidence packet: leaked."),
            "b.md": chapter("Opening with custom marker XYZ."),
        },
        {
            "parts": [{"chapters": ["a.md", "b.md"]}],
            "quality": {"forbidden_paragraph_starts": ["in short"], "forbidden_phrases": ["xyz"]},
        },
    )
    assert codes(report) == ["forbidden-paragraph-start", "reader-facing-scaffold"]
    report = build(tmp_path, dump, {"c.md": chapter("Case study: leaked.")}, {"front": ["c.md"]})
    assert "reader-facing-scaffold" in codes(report)


def test_inventory_flags_unlisted_and_missing_ignored(tmp_path: Path, dump: Dump) -> None:
    report = build(
        tmp_path,
        dump,
        {"a.md": chapter(), "stray.md": "# Stray\n\nx", "skip.md": "# Skip\n\nx"},
        {"parts": [{"chapters": ["a.md"]}], "not_in_book": ["skip.md", "gone.md"]},
    )
    assert codes(report) == ["unlisted-source", "missing-ignored-source"]
    assert report.counts["ignored_file_count"] == 2 and report.counts["source_file_count"] == 3


def test_thresholds(tmp_path: Path, dump: Dump) -> None:
    quality = {
        "expected_chapter_count": 3,
        "minimum_word_count": 1000,
        "word_count_target": 2000,
        "minimum_chapter_words": 50,
        "max_chapter_words_ratio": 2.0,
        "required_back_titles": ["Notes", "Index"],
    }
    files = {
        "a.md": chapter("Short."),
        "b.md": chapter("Word " * 30 + "."),
        "n.md": "# Notes\n\nSome notes.",
    }
    config = {"parts": [{"chapters": ["a.md", "b.md"]}], "back": ["n.md"], "quality": quality}
    report = build(tmp_path, dump, files, config)
    assert codes(report) == [
        "chapter-count",
        "word-count-floor",
        "chapter-word-floor",
        "chapter-word-floor",
        "chapter-imbalance",
        "missing-back-matter",
        "word-count-target",  # warnings are listed after errors
    ]
    assert [i.code for i in report.warnings] == ["word-count-target"]
    strict = {**config, "quality": {**quality, "fail_on_word_count_target": True}}
    assert "word-count-target" in [i.code for i in build(tmp_path, dump, files, strict).issues]


def test_zero_word_chapter_gives_infinite_ratio(tmp_path: Path, dump: Dump) -> None:
    report = build(
        tmp_path,
        dump,
        {"a.md": "# A\n\n", "b.md": chapter()},
        {"parts": [{"chapters": ["a.md", "b.md"]}], "quality": {"max_chapter_words_ratio": 3}},
    )
    assert report.counts["chapter_words_ratio"] == float("inf")
    assert "chapter-imbalance" in codes(report)


def test_formula_phrases_warn_above_threshold(tmp_path: Path, dump: Dump) -> None:
    text = chapter("The danger is one. The danger is two. The danger is three.")
    report = build(
        tmp_path,
        dump,
        {"a.md": text},
        {"parts": [{"chapters": ["a.md"]}], "quality": {"formula_warning_threshold": 2}},
    )
    assert codes(report) == ["repeated-rhetorical-formula"]
    assert report.style_formula_counts["the danger is"] == 3
    quiet = build(tmp_path, dump, {"a.md": text}, {"parts": [{"chapters": ["a.md"]}]})
    assert codes(quiet) == []


def test_config_entries_accept_strings_and_tables() -> None:
    config = {"front": ["f.md"], "parts": [{"chapters": ["c.md"]}, {}], "back": [{"file": "b.md"}]}
    assert ConfigEntries().iterate(config) == [
        ("front", "f.md", "prose", None),
        ("chapter", "c.md", "prose", 1),
        ("back", "b.md", "prose", None),
    ]


def test_balanced_chapters_pass_the_ratio_gate(tmp_path: Path, dump: Dump) -> None:
    report = build(
        tmp_path,
        dump,
        {"a.md": chapter(), "b.md": chapter()},
        {"parts": [{"chapters": ["a.md", "b.md"]}], "quality": {"max_chapter_words_ratio": 3}},
    )
    assert codes(report) == [] and report.counts["chapter_words_ratio"] == 1.0
