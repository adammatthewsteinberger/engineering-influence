# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ScreenplayVisualGrammarCheck: two sections, a primary sets table with four filled columns, and a signature per character."""

from engineering_influence.services.screenplay_visual_grammar_check import (
    ScreenplayVisualGrammarCheck,
)

SETS = "## Primary sets\n| Set | Light | Colour | Texture |\n|---|---|---|---|\n| hive | low, amber | brown | wax |\n\n"
SIGNATURES = "## Character signatures\n- Mara: a torn green scarf\n"


def check(text: str) -> tuple[str, ...]:
    return ScreenplayVisualGrammarCheck().problems(text)


def test_a_complete_visual_grammar_has_no_problems() -> None:
    assert check(SETS + SIGNATURES) == ()


def test_a_missing_section_is_a_problem() -> None:
    assert "the visual grammar needs a '## Character signatures' section" in check(SETS)


def test_the_sets_need_the_four_column_header() -> None:
    wrong = SETS.replace("| Set | Light | Colour | Texture |", "| Set | Light |")
    assert any("'| Set | Light | Colour | Texture |'" in p for p in check(wrong + SIGNATURES))


def test_a_set_with_an_empty_cell_does_not_count() -> None:
    empty = SETS.replace("| hive | low, amber | brown | wax |", "| hive | low, amber |  | wax |")
    assert any("no set with its light" in p for p in check(empty + SIGNATURES))


def test_no_character_signatures_is_a_problem() -> None:
    assert "the character signatures list no character" in check(SETS + "## Character signatures\n")


def test_a_signature_without_a_name_is_a_problem() -> None:
    bad = SETS + "## Character signatures\n- a torn green scarf\n"
    assert any("needs the form 'NAME: signature'" in p for p in check(bad))


def test_a_missing_sets_table_is_reported_without_checking_the_rest() -> None:
    assert "the visual grammar needs a '## Primary sets' section" in check(SIGNATURES)
