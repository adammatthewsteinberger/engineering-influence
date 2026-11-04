"""Pure-logic publishing checks: geometry, normalizer, forbidden content, LaTeX log."""

import pytest

from engineering_influence.publishing.forbidden_content_check import ForbiddenContentCheck
from engineering_influence.publishing.kdp_geometry import KdpGeometry
from engineering_influence.publishing.latex_log_check import LatexLogCheck
from engineering_influence.publishing.text_normalizer import TextNormalizer


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
    assert ForbiddenContentCheck().run(["Some page", "Second Edition here"], "Second Edition") == []


def test_dashes_markers_and_draft_are_reported() -> None:
    texts = ["a — b", "c – d — e", "[CALLOUT x]", "A Draft copy"]
    problems = ForbiddenContentCheck().run(texts, "First Edition")
    assert "page 1: contains an em dash" in problems
    assert "page 2: contains an en dash" in problems
    assert "marker '[CALLOUT' printed in the book" in problems
    assert "the word 'Draft' appears in the book" in problems
    assert "edition line 'First Edition' not found" in problems


def test_edition_must_say_edition() -> None:
    assert ForbiddenContentCheck().run(["text"], "") == [
        "the edition in the config does not say Edition"
    ]


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
