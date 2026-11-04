"""Fonts, typography, typesetters, placement check, and the renderer."""

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image

from engineering_influence.publishing.covers.back_typesetter import BackTypesetter
from engineering_influence.publishing.covers.cover_painter import CoverPainter
from engineering_influence.publishing.covers.cover_renderer import CoverRenderer
from engineering_influence.publishing.covers.cover_style import CoverStyle
from engineering_influence.publishing.covers.font_loader import FontLoader
from engineering_influence.publishing.covers.front_typesetter import FrontTypesetter
from engineering_influence.publishing.covers.kdp_cover_spec import KdpCoverSpec
from engineering_influence.publishing.covers.layout_factory import LayoutFactory
from engineering_influence.publishing.covers.painter_registry import PainterRegistry
from engineering_influence.publishing.covers.spine_typesetter import SpineTypesetter
from engineering_influence.publishing.covers.text_placement_check import TextPlacementCheck
from engineering_influence.publishing.covers.text_recorder import TextRecorder
from engineering_influence.publishing.covers.typography import Typography
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError

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
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(KdpCoverSpec, "MIN_TEXT_PT", 500.0)
    with pytest.raises(BookBuildError, match="KDP's minimum is 500 pt"):
        CoverRenderer(registry, fonts).render(FACTORY.paperback(249), style, meta)
    CoverRenderer(registry, fonts).render(FACTORY.ebook(), style, meta)  # ebooks are not printed


class BlankPainter(CoverPainter):
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
