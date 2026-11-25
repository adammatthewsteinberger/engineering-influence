"""The trim sizes and the paper stocks a book can choose."""

import pytest

from engineering_influence.errors.typesetting.manuscript_error import ManuscriptError
from engineering_influence.models.typesetting.paper_stock import PaperStock
from engineering_influence.models.typesetting.trim_size import TrimSize


def test_a_book_that_sets_no_trim_size_is_six_by_nine() -> None:
    trim = TrimSize.for_name(None)
    assert (trim.name, trim.width_in, trim.height_in, trim.hardcover) == ("6x9", 6.0, 9.0, True)


@pytest.mark.parametrize(
    ("name", "width", "height", "hardcover", "points"),
    [
        ("5x8", 5.0, 8.0, False, (360.0, 576.0)),
        ("5.5x8.5", 5.5, 8.5, True, (396.0, 612.0)),
        ("6x9", 6.0, 9.0, True, (432.0, 648.0)),
    ],
)
def test_each_trim_size_knows_its_dimensions_and_whether_kdp_prints_a_hardcover_at_it(
    name: str, width: float, height: float, hardcover: bool, points: tuple[float, float]
) -> None:
    trim = TrimSize.for_name(name)
    assert (trim.width_in, trim.height_in, trim.hardcover, trim.points()) == (
        width,
        height,
        hardcover,
        points,
    )


def test_the_trim_sizes_are_listed_in_the_documented_order() -> None:
    assert TrimSize.names() == ("5x8", "5.5x8.5", "6x9")


@pytest.mark.parametrize("name", ["7x10", "6 x 9", "", "A5", "6x9 "])
def test_an_unknown_trim_size_is_refused_with_the_valid_ones_named(name: str) -> None:
    with pytest.raises(ManuscriptError, match="5x8, 5.5x8.5, 6x9"):
        TrimSize.for_name(name)


@pytest.mark.parametrize(("width", "height"), [(0, 9), (6, 0), (-1, 9)])
def test_a_trim_size_needs_positive_dimensions(width: float, height: float) -> None:
    with pytest.raises(ValueError, match="positive width and height"):
        TrimSize("bad", width, height, hardcover=False)


def test_a_book_that_sets_no_paper_is_on_white_paper() -> None:
    paper = PaperStock.for_name(None)
    assert (paper.name, paper.inches_per_page) == ("white", 0.002252)


def test_cream_paper_is_thicker_than_white() -> None:
    cream, white = PaperStock.for_name("cream"), PaperStock.for_name("white")
    assert cream.inches_per_page == 0.0025
    assert cream.inches_per_page > white.inches_per_page


def test_the_paper_stocks_are_listed_in_the_documented_order() -> None:
    assert PaperStock.names() == ("white", "cream")


@pytest.mark.parametrize("name", ["glossy", "", "Cream", "color"])
def test_an_unknown_paper_is_refused_with_the_valid_ones_named(name: str) -> None:
    with pytest.raises(ManuscriptError, match="white, cream"):
        PaperStock.for_name(name)


@pytest.mark.parametrize("thickness", [0, -0.001])
def test_paper_needs_a_positive_thickness(thickness: float) -> None:
    with pytest.raises(ValueError, match="positive thickness"):
        PaperStock("bad", thickness)
