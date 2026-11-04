"""Boxes, layouts, KDP geometry, and layout checks."""

import dataclasses

import pytest

from engineering_influence.publishing.covers.box import Box
from engineering_influence.publishing.covers.cover_layout import CoverLayout
from engineering_influence.publishing.covers.layout_check import LayoutCheck
from engineering_influence.publishing.covers.layout_factory import LayoutFactory

FACTORY = LayoutFactory()


def test_box_dimensions_and_inset_defaults() -> None:
    box = Box(1, 2, 7, 11)
    assert (box.w, box.h) == (6, 9)
    assert box.inset(1) == Box(2, 3, 6, 10)
    assert box.inset(1, 2) == Box(2, 4, 6, 9)
    assert box.inset(1, 2, 3) == Box(2, 4, 4, 9)
    assert box.inset(1, 2, 3, 4) == Box(2, 4, 4, 7)


def test_layout_pixels_round_up_to_the_exact_page() -> None:
    layout = CoverLayout("x", 2.0, 1.0001, 300, Box(0, 0, 1, 1), Box(0, 0, 1, 1))
    assert layout.px == (600, 301)
    assert layout.to_px(0.5) == 150
    assert layout.box_px(Box(0.1, 0.2, 0.3, 0.4)) == (30, 60, 90, 120)


def test_ebook_layout_matches_kindle_pixels() -> None:
    layout = FACTORY.ebook()
    assert layout.px == (1600, 2560) and layout.kind == "ebook"
    assert layout.back is None and layout.spine_safe is None and layout.barcode is None


def test_paperback_spine_grows_with_pages() -> None:
    layout = FACTORY.paperback(249)
    assert layout.spine is not None and layout.spine.w == pytest.approx(249 * 0.002252)
    assert layout.px == (3844, 2775) and layout.spine_safe is not None
    assert layout.barcode is not None and layout.back is not None
    assert layout.barcode.x1 == pytest.approx(layout.back.x1 - 0.25)


def test_thin_books_get_no_spine_text() -> None:
    assert FACTORY.paperback(78).spine_safe is None
    assert FACTORY.paperback(79).spine_safe is not None
    assert FACTORY.hardcover(78).spine_safe is None
    assert FACTORY.hardcover(79).spine_safe is not None


def test_hardcover_has_boards_hinge_and_wrap() -> None:
    layout = FACTORY.hardcover(360)
    assert layout.kind == "hardcover" and layout.px == (4373, 3126)
    assert layout.spine is not None and layout.spine.w == pytest.approx(360 * 0.002252 + 4.8 / 25.4)
    assert layout.back_safe is not None and layout.barcode is not None


def test_standard_layouts_pass_every_check() -> None:
    check = LayoutCheck()
    assert check.run(FACTORY.ebook()) == []
    assert check.run(FACTORY.paperback(249)) == []
    assert check.run(FACTORY.paperback(40)) == []
    assert check.run(FACTORY.hardcover(360)) == []
    assert check.run(FACTORY.hardcover(40)) == []


def moved(layout: CoverLayout, **boxes: Box) -> CoverLayout:
    return dataclasses.replace(layout, **boxes)


def test_paperback_violations() -> None:
    base = FACTORY.paperback(249)
    assert base.back is not None and base.spine is not None and base.back_safe is not None
    assert base.spine_safe is not None and base.barcode is not None
    wrong = moved(
        base,
        front_safe=base.front.inset(0.0),
        back_safe=base.back.inset(0.0),
        spine_safe=base.spine.inset(0.0),
        barcode=Box(0, 0, 99, 99),
    )
    problems = LayoutCheck().run(wrong)
    assert "[paperback] layout: front text must sit 0.125 in inside the trim" in problems
    assert "[paperback] layout: back text must sit 0.125 in inside the trim" in problems
    assert "[paperback] layout: spine text needs 0.0625 in on each side" in problems
    assert "[paperback] layout: barcode box must sit on the back cover" in problems


def test_hardcover_violations() -> None:
    base = FACTORY.hardcover(249)
    assert base.back is not None and base.spine is not None and base.back_safe is not None
    assert base.barcode is not None
    wrong = moved(
        base,
        front_safe=base.front.inset(0.0),
        back_safe=base.back.inset(0.0),
        spine_safe=base.spine.inset(0.0),
        barcode=Box(base.back.x1, base.height - 0.1, base.back.x1 + 1, base.height),
    )
    problems = LayoutCheck().run(wrong)
    assert "[hardcover] layout: text must stay out of the 10 mm hinge" in problems
    assert "[hardcover] layout: front text must sit 0.125 in inside the board edge" in problems
    assert "[hardcover] layout: back text must sit 0.125 in inside the board edge" in problems
    assert "[hardcover] layout: spine text needs 0.0625 in on each side" in problems
    assert "[hardcover] layout: barcode must sit 0.76 in above the bottom edge" in problems
    assert "[hardcover] layout: barcode must sit 0.25 in from the hinge" in problems


@pytest.mark.parametrize("kind", ["paperback", "hardcover"])
def test_incomplete_print_layouts_are_rejected(kind: str) -> None:
    layout = dataclasses.replace(FACTORY.ebook(), kind=kind)
    with pytest.raises(ValueError, match="needs back, spine, and barcode"):
        LayoutCheck().run(layout)
