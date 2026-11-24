"""Fonts, typography, typesetters, placement check, and the renderer."""

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image

from engineering_influence.errors.typesetting.back_cover_text_too_long_error import (
    BackCoverTextTooLongError,
)
from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.infrastructure.covers.back_typesetter import BackTypesetter
from engineering_influence.infrastructure.covers.cover_renderer import CoverRenderer
from engineering_influence.infrastructure.covers.font_loader import FontLoader
from engineering_influence.infrastructure.covers.front_typesetter import FrontTypesetter
from engineering_influence.infrastructure.covers.painter_registry import PainterRegistry
from engineering_influence.infrastructure.covers.spine_typesetter import SpineTypesetter
from engineering_influence.infrastructure.covers.text_placement_check import TextPlacementCheck
from engineering_influence.infrastructure.covers.typography import Typography
from engineering_influence.interfaces.cover_painter_interface import CoverPainterInterface
from engineering_influence.models.covers.cover_style import CoverStyle
from engineering_influence.models.covers.kdp_cover_spec import KdpCoverSpec
from engineering_influence.models.covers.layout_factory import LayoutFactory
from engineering_influence.models.covers.text_recorder import TextRecorder
from engineering_influence.models.typesetting.paper_stock import PaperStock
from engineering_influence.models.typesetting.trim_size import TrimSize

FACTORY = LayoutFactory()


def test_font_loader_searches_directories_in_order(font_path: Path, tmp_path: Path) -> None:
    loader = FontLoader([tmp_path, font_path])
    font = loader.load("EBGaramond-Regular.otf", 20.2)
    assert font.size == 21
    assert loader.load("EBGaramond-Regular.otf", 1).size == 6
    with pytest.raises(BookBuildError, match="cover font not found: Nope.otf"):
        loader.load("Nope.otf", 20)


def test_text_recorder_tracks_the_smallest_run() -> None:
    recorder = TextRecorder()
    assert recorder.smallest() is None
    recorder.record(40)
    recorder.record(12)
    assert recorder.smallest() == 12


def typography(fonts: FontLoader) -> Typography:
    return Typography(fonts, TextRecorder())


def test_typography_measures_wraps_and_fits(fonts: FontLoader) -> None:
    t = typography(fonts)
    f = t.font("EBGaramond-Regular.otf", 40)
    assert t.tracked_width(f, "abc", 0) == f.getlength("abc")
    assert t.tracked_width(f, "abc", 10) == pytest.approx(
        f.getlength("a") + f.getlength("b") + f.getlength("c") + 20
    )
    assert t.wrap_px("", f, 100) == []
    assert t.wrap_px("aaa bbb ccc", f, f.getlength("aaa bbb") + 1) == ["aaa bbb", "ccc"]
    assert t.wrap_px("Unbreakableextremelylongword", f, 5) == ["Unbreakableextremelylongword"]
    size = t.fit_size("EBGaramond-Regular.otf", ["Wide line", "x"], 0.1, 500)
    fitted = t.font("EBGaramond-Regular.otf", size)
    assert t.tracked_width(fitted, "Wide line", 0.1 * size) == pytest.approx(500, rel=0.05)
    assert isinstance(t.cap_top(f, "Hello"), int)
    assert t.plain("**bold** _it_ `code`") == "bold it code"


def test_typography_color_and_size_floor(fonts: FontLoader) -> None:
    t = typography(fonts)
    assert t.c8((0, 0.5, 2.0)) == (0, 128, 255, 255)
    assert t.c8((-1, 1, 1)) == (0, 255, 255, 255)
    ebook, paperback = FACTORY.ebook(), FACTORY.paperback(249)
    assert t.floor_px(ebook, 1.0) == 1.0
    assert t.floor_px(paperback, 1.0) == pytest.approx(KdpCoverSpec.TEXT_FLOOR_IN * 300)
    assert t.floor_px(paperback, 999.0) == 999.0


def test_draw_tracked_records_sizes_with_and_without_tracking(fonts: FontLoader) -> None:
    recorder = TextRecorder()
    t = Typography(fonts, recorder)
    from PIL import ImageDraw

    image = Image.new("RGBA", (300, 100), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    f = t.font("EBGaramond-Regular.otf", 30)
    t.draw_tracked(draw, (5, 5), "Plain", f, (255, 255, 255, 255), 0)
    t.draw_tracked(draw, (5, 50), "Spaced", f, (255, 255, 255, 255), 6)
    assert recorder.smallest() == 30 and image.getchannel("A").getbbox() is not None


def layer_for(layout: Any) -> Image.Image:
    return Image.new("RGBA", layout.px, (0, 0, 0, 0))


def test_front_typesetter_variants(
    fonts: FontLoader, style: CoverStyle, meta: dict[str, Any]
) -> None:
    layout = FACTORY.ebook()
    for upper, on_top, serif in ((True, False, True), (False, True, False)):
        style.title_case_upper, style.author_on_top = upper, on_top
        style.extra["subtitle_serif"] = serif
        layer = layer_for(layout)
        FrontTypesetter(typography(fonts)).typeset(layer, layout, style, meta)
        assert layer.getchannel("A").getbbox() is not None
    assert TextPlacementCheck().run(layer, layout) == []
    meta = {k: v for k, v in meta.items() if k != "subtitle"}
    FrontTypesetter(typography(fonts)).typeset(layer_for(layout), layout, style, meta)


def test_serif_subtitle_defaults_to_the_cormorant_name_check(
    fonts: FontLoader, style: CoverStyle, meta: dict[str, Any]
) -> None:
    del style.extra["subtitle_serif"]
    style.subtitle_font = "EBGaramond-Italic.otf"
    layout = FACTORY.ebook()
    layer = layer_for(layout)
    FrontTypesetter(typography(fonts)).typeset(layer, layout, style, meta)
    assert layer.getchannel("A").getbbox() is not None


def test_back_typesetter_draws_description_bio_and_imprint(
    fonts: FontLoader, style: CoverStyle, meta: dict[str, Any]
) -> None:
    layout = FACTORY.paperback(249)
    layer = layer_for(layout)
    BackTypesetter(typography(fonts)).typeset(layer, layout, style, meta)
    assert TextPlacementCheck().run(layer, layout) == []
    box = layout.box_px(layout.back_safe)  # type: ignore[arg-type]
    inked = np.asarray(layer.getchannel("A"))[box[1] : box[3], box[0] : box[2]]
    assert (inked > 8).sum() > 1000


def test_back_typesetter_skips_ebooks_and_works_without_a_website(
    fonts: FontLoader, style: CoverStyle, meta: dict[str, Any]
) -> None:
    ebook = FACTORY.ebook()
    layer = layer_for(ebook)
    BackTypesetter(typography(fonts)).typeset(layer, ebook, style, meta)
    assert layer.getchannel("A").getbbox() is None
    layout = FACTORY.paperback(249)
    meta.pop("website")
    layer = layer_for(layout)
    BackTypesetter(typography(fonts)).typeset(layer, layout, style, meta)
    assert layer.getchannel("A").getbbox() is not None


def test_back_typesetter_shrinks_long_copy_to_fit(
    fonts: FontLoader, style: CoverStyle, meta: dict[str, Any]
) -> None:
    layout = FACTORY.paperback(249)
    meta["description"] = "\n\n".join(["A very long paragraph of back cover copy. " * 12] * 6)
    layer = layer_for(layout)
    BackTypesetter(typography(fonts)).typeset(layer, layout, style, meta)
    assert TextPlacementCheck().run(layer, layout) == []


def test_spine_typesetter_cases(fonts: FontLoader, style: CoverStyle, meta: dict[str, Any]) -> None:
    thin = FACTORY.paperback(40)
    layer = layer_for(thin)
    SpineTypesetter(typography(fonts)).typeset(layer, thin, style, meta)
    assert layer.getchannel("A").getbbox() is None  # too thin for spine text
    narrow = FACTORY.paperback(79)
    layer = layer_for(narrow)
    SpineTypesetter(typography(fonts)).typeset(layer, narrow, style, meta)
    assert layer.getchannel("A").getbbox() is None  # spine cannot hold a legible title
    normal = FACTORY.paperback(249)
    layer = layer_for(normal)
    SpineTypesetter(typography(fonts)).typeset(layer, normal, style, meta)
    assert layer.getchannel("A").getbbox() is not None
    assert TextPlacementCheck().run(layer, normal) == []


def test_spine_shrinks_a_title_that_is_too_long(
    fonts: FontLoader, style: CoverStyle, meta: dict[str, Any]
) -> None:
    style.title_lines = [
        "An Extremely Long Title That Cannot Possibly",
        "Fit Along The Spine Of A Thin Book",
    ]
    style.title_case_upper = False
    layout = FACTORY.paperback(120)
    layer = layer_for(layout)
    SpineTypesetter(typography(fonts)).typeset(layer, layout, style, meta)
    assert TextPlacementCheck().run(layer, layout) == []
    ebookish = FACTORY.hardcover(250)
    SpineTypesetter(typography(fonts)).typeset(layer_for(ebookish), ebookish, style, meta)


def test_placement_check_allows_a_glyph_to_overhang_the_safe_area_a_little_but_not_a_lot() -> None:
    layout = FACTORY.paperback(249)
    box = layout.box_px(layout.back_safe)  # type: ignore[arg-type]
    middle = (box[1] + box[3]) // 2
    layer = layer_for(layout)
    layer.putpixel((box[0] - round(0.05 * layout.ppi), middle), (255, 255, 255, 255))
    assert TextPlacementCheck().run(layer, layout) == []
    layer = layer_for(layout)
    layer.putpixel((box[0] - round(0.09 * layout.ppi), middle), (255, 255, 255, 255))
    assert "text pixels outside the safe areas" in TextPlacementCheck().run(layer, layout)[0]


def test_placement_check_flags_stray_text_and_barcode_overlap() -> None:
    layout = FACTORY.paperback(249)
    layer = layer_for(layout)
    layer.putpixel((2, 2), (255, 255, 255, 255))
    problems = TextPlacementCheck().run(layer, layout)
    assert problems and "text pixels outside the safe areas" in problems[0]
    layer = layer_for(layout)
    x0, y0, _x1, _y1 = layout.box_px(layout.barcode)  # type: ignore[arg-type]
    layer.putpixel((x0 + 5, y0 + 5), (255, 255, 255, 255))
    assert "text inside the barcode area" in TextPlacementCheck().run(layer, layout)


def test_ebook_layout_has_no_barcode_to_check() -> None:
    layout = FACTORY.ebook()
    assert TextPlacementCheck().run(layer_for(layout), layout) == []


def test_renderer_produces_rgb_covers(
    fonts: FontLoader, registry: PainterRegistry, style: CoverStyle, meta: dict[str, Any]
) -> None:
    renderer = CoverRenderer(registry, fonts)
    ebook = renderer.render(FACTORY.ebook(), style, meta)
    assert ebook.mode == "RGB" and ebook.size == (1600, 2560)
    paperback = renderer.render(FACTORY.paperback(249), style, meta)
    assert paperback.size == (3844, 2775)
    again = renderer.render(FACTORY.ebook(), style, meta)
    assert again.tobytes() == ebook.tobytes()


def test_renderer_fails_on_text_outside_the_safe_area(
    fonts: FontLoader, registry: PainterRegistry, style: CoverStyle, meta: dict[str, Any]
) -> None:
    style.title_frac = 3.0
    with pytest.raises(
        BookBuildError, match=r"\[ebook\] cover text check failed: .*outside the safe areas"
    ):
        CoverRenderer(registry, fonts).render(FACTORY.ebook(), style, meta)


def test_renderer_enforces_the_minimum_print_text_size(
    fonts: FontLoader,
    registry: PainterRegistry,
    style: CoverStyle,
    meta: dict[str, Any],
) -> None:
    strict = CoverRenderer(registry, fonts, min_text_pt=500.0)
    with pytest.raises(BookBuildError, match="KDP's minimum is 500 pt"):
        strict.render(FACTORY.paperback(249), style, meta)
    strict.render(FACTORY.ebook(), style, meta)  # ebooks are not printed


class BlankPainter(CoverPainterInterface):
    def paint(self, layout: Any, style: CoverStyle) -> Any:
        return np.zeros((*reversed(layout.px), 3), np.float32)


def test_renderer_uses_the_painter_named_in_the_style(
    fonts: FontLoader, style: CoverStyle, meta: dict[str, Any]
) -> None:
    registry = PainterRegistry()
    registry.register("blank", BlankPainter())
    style.painter = "blank"
    image = CoverRenderer(registry, fonts).render(FACTORY.ebook(), style, meta)
    assert image.getpixel((0, 0)) == (0, 0, 0) or max(image.getpixel((0, 0))) <= 1
    style.painter = "nonexistent"
    with pytest.raises(BookBuildError, match="no cover painter named 'nonexistent'"):
        CoverRenderer(registry, fonts).render(FACTORY.ebook(), style, meta)


SENTENCE = (
    "The keeper climbed the stairs every evening, counting the steps as her mother taught her. "
)


def blurb(characters: int) -> str:
    """Original filler of about this many characters, in paragraphs of about 400."""
    text = (SENTENCE * (characters // len(SENTENCE) + 1))[:characters].rstrip()
    return "\n\n".join(text[i : i + 400] for i in range(0, len(text), 400))


def trimmed_factory(trim: str) -> LayoutFactory:
    return LayoutFactory(TrimSize.for_name(trim), PaperStock.for_name("white"))


def too_long(
    fonts: FontLoader, style: CoverStyle, meta: dict[str, Any], layout: Any, characters: int
) -> BackCoverTextTooLongError:
    meta["description"] = blurb(characters)
    with pytest.raises(BackCoverTextTooLongError) as raised:
        BackTypesetter(typography(fonts)).typeset(layer_for(layout), layout, style, meta)
    return raised.value


def test_a_description_that_cannot_fit_above_the_barcode_is_refused_with_the_numbers(
    fonts: FontLoader, style: CoverStyle, meta: dict[str, Any]
) -> None:
    error = too_long(fonts, style, meta, trimmed_factory("5x8").paperback(249), 4000)
    assert 0 < error.capacity < error.characters
    assert error.overflow_in > 0
    assert f"{error.characters} characters" in str(error)
    assert f"about {error.capacity} fit" in str(error)
    assert isinstance(error, BookBuildError)


@pytest.mark.parametrize("trim", ["5x8", "5.5x8.5", "6x9"])
def test_the_reported_capacity_really_fits_and_a_little_more_does_not(
    fonts: FontLoader, style: CoverStyle, meta: dict[str, Any], trim: str
) -> None:
    layout = trimmed_factory(trim).paperback(249)
    capacity = too_long(fonts, style, meta, layout, 4500).capacity

    meta["description"] = blurb(capacity)
    layer = layer_for(layout)
    BackTypesetter(typography(fonts)).typeset(layer, layout, style, meta)
    assert TextPlacementCheck().run(layer, layout) == []

    assert too_long(fonts, style, meta, layout, capacity + 300).capacity >= capacity - 50


def test_a_narrower_trim_size_carries_less_back_cover_text(
    fonts: FontLoader, style: CoverStyle, meta: dict[str, Any]
) -> None:
    capacity = {
        trim: too_long(fonts, style, meta, trimmed_factory(trim).paperback(249), 6000).capacity
        for trim in ("5x8", "5.5x8.5", "6x9")
    }
    assert capacity["5x8"] < capacity["5.5x8.5"] < capacity["6x9"]


@pytest.mark.parametrize(
    ("trim", "kind"),
    [
        ("5x8", "paperback"),
        ("5.5x8.5", "paperback"),
        ("5.5x8.5", "hardcover"),
        ("6x9", "hardcover"),
    ],
)
def test_text_at_the_limit_never_reaches_the_barcode_area_at_any_size(
    fonts: FontLoader, style: CoverStyle, meta: dict[str, Any], trim: str, kind: str
) -> None:
    made = trimmed_factory(trim)
    layout = made.paperback(249) if kind == "paperback" else made.hardcover(249)
    capacity = too_long(fonts, style, meta, layout, 6000).capacity
    meta["description"] = blurb(capacity)
    layer = layer_for(layout)
    BackTypesetter(typography(fonts)).typeset(layer, layout, style, meta)
    assert layout.barcode is not None
    x0, y0, x1, y1 = layout.box_px(layout.barcode)
    assert not (np.asarray(layer.getchannel("A")) > 8)[y0:y1, x0:x1].any()
    assert TextPlacementCheck().run(layer, layout) == []


@pytest.mark.parametrize("trim", ["5x8", "5.5x8.5", "6x9"])
def test_ink_in_the_barcode_area_is_always_caught(trim: str) -> None:
    made = trimmed_factory(trim)
    layouts = [made.paperback(249)] + (
        [made.hardcover(249)] if TrimSize.for_name(trim).hardcover else []
    )
    for layout in layouts:
        layer = layer_for(layout)
        assert layout.barcode is not None
        x0, y0, _, _ = layout.box_px(layout.barcode)
        layer.paste((0, 0, 0, 255), (x0 + 5, y0 + 5, x0 + 40, y0 + 40))
        assert "text inside the barcode area" in TextPlacementCheck().run(layer, layout)
