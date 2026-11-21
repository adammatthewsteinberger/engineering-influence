"""Pure-logic publishing checks: geometry, normalizer, forbidden content, LaTeX log."""

from pathlib import Path

import pytest

from engineering_influence.models.publishing.path_relativizer import PathRelativizer
from engineering_influence.models.typesetting.text_policy import TextPolicy
from engineering_influence.services.publishing.forbidden_content_check import ForbiddenContentCheck
from engineering_influence.services.publishing.kdp_geometry import KdpGeometry
from engineering_influence.services.publishing.latex_log_check import LatexLogCheck
from engineering_influence.services.publishing.text_normalizer import TextNormalizer

NONFICTION = TextPolicy.for_name(None)
NOVEL = TextPolicy.for_name("novel")


@pytest.mark.parametrize(
    ("pages", "gutter"), [(100, 0.375), (150, 0.375), (151, 0.5), (600, 0.75), (828, 0.875)]
)
def test_gutter_grows_with_page_count(pages: int, gutter: float) -> None:
    assert KdpGeometry().gutter_inches(pages) == gutter


def test_gutter_rejects_books_kdp_cannot_print() -> None:
    with pytest.raises(ValueError, match="829-page"):
        KdpGeometry().gutter_inches(829)


def test_normalizer_folds_quotes_case_and_punctuation() -> None:
    assert TextNormalizer().normalize("It’s  “A” Test!") == "it'satest"


def test_clean_text_passes() -> None:
    clean = ["Some page", "Second Edition here"]
    assert ForbiddenContentCheck().run(clean, "Second Edition", NONFICTION) == []


def test_dashes_markers_and_draft_are_reported() -> None:
    texts = ["a — b", "c – d — e", "[CALLOUT x]", "A Draft copy"]
    problems = ForbiddenContentCheck().run(texts, "First Edition", NONFICTION)
    assert "page 1: contains an em dash" in problems
    assert "page 2: contains an en dash" in problems
    assert "marker '[CALLOUT' printed in the book" in problems
    assert "the word 'Draft' appears in the book" in problems
    assert "edition line 'First Edition' not found" in problems


def test_edition_must_say_edition() -> None:
    assert ForbiddenContentCheck().run(["text"], "", NONFICTION) == [
        "the edition in the config does not say Edition"
    ]


def problems_for(texts: list[str], policy: TextPolicy) -> list[str]:
    """The problems in some pages that otherwise carry the edition line the check insists on."""
    return ForbiddenContentCheck().run([*texts, "First Edition"], "First Edition", policy)


def test_a_novel_may_use_em_dashes_but_en_dashes_are_still_refused() -> None:
    assert problems_for(["wait \u2014 what"], NOVEL) == []
    assert problems_for(["wait \u2014 what", "1990\u20131995"], NOVEL) == [
        "page 2: contains an en dash"
    ]


def test_nonfiction_refuses_the_same_em_dash() -> None:
    assert problems_for(["wait \u2014 what"], NONFICTION) == ["page 1: contains an em dash"]


def test_a_character_in_a_novel_may_say_draft() -> None:
    assert problems_for(["\u201cDraft beer is a penny,\u201d she said."], NOVEL) == []


def test_dialogue_that_runs_across_a_page_break_still_counts_as_dialogue() -> None:
    assert problems_for(["\u201cDraft", "beer,\u201d she said."], NOVEL) == []


def test_a_novel_still_refuses_draft_in_narration() -> None:
    assert problems_for(["A Draft copy sat on the desk."], NOVEL) == [
        "the word 'Draft' appears in the book"
    ]


def test_a_novel_refuses_draft_outside_the_quotes_even_when_it_also_appears_inside() -> None:
    texts = ["\u201cDraft,\u201d she said. Draft was stamped on the page."]
    assert problems_for(texts, NOVEL) == ["the word 'Draft' appears in the book"]


def test_nonfiction_refuses_draft_even_inside_quotation_marks() -> None:
    assert problems_for(["\u201cDraft beer,\u201d she said."], NONFICTION) == [
        "the word 'Draft' appears in the book"
    ]


def test_an_opening_quote_that_never_closes_cannot_hide_a_later_draft() -> None:
    text = "\u201c" + "x" * 600 + " Draft stamped here \u201d"
    assert problems_for([text], NOVEL) == ["the word 'Draft' appears in the book"]


def test_log_reports_glyphs_and_only_significant_overfull_lines() -> None:
    log = (
        "Missing character: There is no ☃ (U+2603) in font x\n"
        "Overfull \\hbox (0.5pt too wide)\nOverfull \\hbox (4.0pt too wide)\n"
    )
    assert LatexLogCheck().run(log) == [
        "missing glyph ☃ (U+2603)",
        "1 overfull lines (worst 4.0pt)",
    ]


def test_log_ignores_tiny_overfull_lines() -> None:
    assert LatexLogCheck().run("Overfull \\hbox (0.5pt too wide)") == []


def test_relativizer_returns_root_relative_or_absolute_paths(tmp_path: Path) -> None:
    relativizer = PathRelativizer(tmp_path / "root")
    inside = tmp_path / "root" / "a" / "b.md"
    outside = tmp_path / "elsewhere.md"
    assert relativizer.relative(inside) == "a/b.md"
    assert relativizer.relative(outside) == str(outside.resolve())
