# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ScreenplayLength: the page count against the ceiling, and the three-hour note."""

import pytest

from engineering_influence.services.screenplay_length import ScreenplayLength


def test_a_screenplay_within_three_hours_has_no_problem() -> None:
    assert ScreenplayLength().problems(164) == ()


def test_a_screenplay_past_three_hours_but_within_the_ceiling_is_noted() -> None:
    notes = ScreenplayLength().problems(195)
    assert len(notes) == 1
    assert "past three hours" in notes[0]


def test_a_screenplay_over_the_ceiling_fails() -> None:
    problems = ScreenplayLength().problems(196)
    assert len(problems) == 1
    assert "over the 195-page ceiling" in problems[0]


def test_the_ceiling_can_be_set_for_another_film() -> None:
    assert ScreenplayLength(ceiling_pages=170).problems(175) != ()


def test_an_empty_screenplay_is_a_problem() -> None:
    assert "not a screenplay" in ScreenplayLength().problems(0)[0]


def test_a_non_positive_ceiling_is_refused() -> None:
    with pytest.raises(ValueError):
        ScreenplayLength(ceiling_pages=0)
