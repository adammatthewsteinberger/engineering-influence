# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""ChapterCount: one chapter per 3,500 words, between 3 and 30, and an outline within 15% of that is right."""

import pytest

from engineering_influence.models.chapter_count import ChapterCount


def test_a_target_gives_one_chapter_per_3500_words_rounded_to_the_nearest() -> None:
    assert ChapterCount.for_target(100_000) == 29
    assert ChapterCount.for_target(10_500) == 3
    assert ChapterCount.for_target(12_000) == 3


def test_the_count_is_kept_between_three_and_thirty() -> None:
    assert ChapterCount.for_target(1) == 3
    assert ChapterCount.for_target(20_000) == 6
    assert ChapterCount.for_target(500_000) == 30


def test_no_target_has_no_number_so_the_model_chooses() -> None:
    assert ChapterCount.for_target(None) is None
    assert ChapterCount.mismatch(None, 1) is None


@pytest.mark.parametrize("chapters", [25, 29, 33])
def test_an_outline_within_fifteen_percent_of_the_count_is_right(chapters: int) -> None:
    assert ChapterCount.mismatch(100_000, chapters) is None


@pytest.mark.parametrize("chapters", [9, 24, 34, 60])
def test_an_outline_outside_fifteen_percent_names_the_count_to_write(chapters: int) -> None:
    problem = ChapterCount.mismatch(100_000, chapters)
    assert problem is not None
    assert f"the outline has {chapters} chapters" in problem
    assert "needs about 29" in problem and "write 29 chapters" in problem
