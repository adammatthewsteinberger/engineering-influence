"""End-to-end cover builds in a temporary project."""

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from engineering_influence.errors.typesetting.back_cover_text_too_long_error import (
    BackCoverTextTooLongError,
)
from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.errors.typesetting.manuscript_error import ManuscriptError
from engineering_influence.infrastructure.covers.cover_builder import CoverBuilder
from engineering_influence.infrastructure.covers.interfaces.ebook_cover_verifier_interface import (
    EbookCoverVerifierInterface,
)
from engineering_influence.infrastructure.covers.painter_registry import PainterRegistry
from engineering_influence.interfaces.cover_painter_interface import CoverPainterInterface
from engineering_influence.models.covers.cover_style import CoverStyle
from engineering_influence.models.publishing.project_layout import ProjectLayout

FILES = (
    "ebook.jpg",
    "ebook.tif",
    "front.tif",
    "back.tif",
    "paperback-wrap.tif",
    "paperback-wrap.pdf",
    "hardcover-wrap.tif",
    "hardcover-wrap.pdf",
)


def blank_pdf(path: Path, pages: int) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(432, 648)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        writer.write(handle)


def project(root: Path, extra: str = "") -> ProjectLayout:
    (root / "books").mkdir()
    (root / "books" / "demo.toml").write_text(
        'title = "Demo Cover"\nsubtitle = "A Subtitle"\nauthor = "Ann Author"\npublisher = "Pub House"\n'
        'website = "https://pub.example"\ndescription = "A back cover blurb.\\n\\nMore of it."\n'
        'author_bio = "Ann writes."\n' + extra,
        encoding="utf-8",
    )
    blank_pdf(root / "output" / "demo.pdf", 120)
    return ProjectLayout(root)


def test_builds_and_verifies_every_cover_file(tmp_path: Path) -> None:
    layout = project(tmp_path)
    out = CoverBuilder(layout).build("demo")
    assert out == tmp_path / "output" / "covers" / "demo"
    assert sorted(p.name for p in out.iterdir()) == sorted(f"demo-{f}" for f in FILES)
    with Image.open(out / "demo-ebook.tif") as ebook:
        assert ebook.size == (1600, 2560)
    with Image.open(out / "demo-paperback-wrap.tif") as wrap:
        assert wrap.size == (
            3757,
            2775,
        )  # 120 pages (3756.07 px, rounded up): 0.25 + 12 + 120 * 0.002252 in


def test_is_deterministic(tmp_path: Path) -> None:
    layout = project(tmp_path)
    first = (CoverBuilder(layout).build("demo") / "demo-ebook.jpg").read_bytes()
    second = (CoverBuilder(layout).build("demo") / "demo-ebook.jpg").read_bytes()
    assert first == second


def test_writes_previews_and_uses_a_compact_hardcover_interior(tmp_path: Path) -> None:
    layout = project(tmp_path, extra="[formats]\nhardcover_max_pages = 200\n")
    blank_pdf(tmp_path / "output" / "demo-hardcover.pdf", 90)
    out = CoverBuilder(layout).build(
        "demo", preview=True, hardcover_pdf=Path("output/demo-hardcover.pdf")
    )
    assert (out / "demo-ebook-preview.jpg").exists() and (
        out / "demo-hardcover-preview.jpg"
    ).exists()
    with Image.open(out / "demo-ebook-preview.jpg") as preview:
        assert preview.size == (400, 640)
    absolute = CoverBuilder(layout).build(
        "demo", hardcover_pdf=tmp_path / "output" / "demo-hardcover.pdf"
    )
    assert absolute == out


def test_rejects_a_hardcover_interior_over_the_configured_maximum(tmp_path: Path) -> None:
    layout = project(tmp_path, extra="[formats]\nhardcover_max_pages = 50\n")
    blank_pdf(tmp_path / "output" / "big.pdf", 90)
    with pytest.raises(
        BookBuildError, match="hardcover interior has 90 pages; configured maximum is 50"
    ):
        CoverBuilder(layout).build("demo", hardcover_pdf=Path("output/big.pdf"))


def test_a_malformed_formats_table_falls_back_to_the_default_maximum(tmp_path: Path) -> None:
    layout = project(tmp_path, extra="formats = 7\n")
    blank_pdf(tmp_path / "output" / "hc.pdf", 90)
    assert CoverBuilder(layout).build("demo", hardcover_pdf=Path("output/hc.pdf")).is_dir()


def test_reports_missing_inputs_and_unsafe_slugs(tmp_path: Path) -> None:
    layout = project(tmp_path)
    builder = CoverBuilder(layout)
    with pytest.raises(BookBuildError, match="no such book config"):
        builder.build("absent")
    with pytest.raises(BookBuildError, match="invalid book slug"):
        builder.build("../demo")
    (tmp_path / "output" / "demo.pdf").unlink()
    with pytest.raises(BookBuildError, match="build the interior first"):
        builder.build("demo")


class WhitePainter(CoverPainterInterface):
    def paint(self, layout: Any, style: CoverStyle) -> Any:
        return np.ones((*reversed(layout.px), 3), np.float32)


def test_a_light_ebook_cover_gets_the_gray_border_and_still_verifies(tmp_path: Path) -> None:
    layout = project(tmp_path)
    registry = PainterRegistry()
    registry.register("white", WhitePainter())
    from engineering_influence.models.covers.builtin_cover_style import BuiltinCoverStyle

    style = BuiltinCoverStyle().for_book({"title": "Demo Cover"})
    style.painter = "white"
    for field in (
        "title_color",
        "subtitle_color",
        "author_color",
        "body_color",
        "accent",
        "spine_color",
    ):
        setattr(style, field, (0.05, 0.05, 0.1))
    out = CoverBuilder(layout, registry=registry, styles={"demo": style}).build("demo")
    with Image.open(out / "demo-ebook.tif") as ebook:
        assert ebook.getpixel((0, 0)) == (128, 128, 128)
        assert ebook.getpixel((800, 8))[0] > 250  # the art itself is untouched inside the frame


class FailingEbookVerifier(EbookCoverVerifierInterface):
    def run(self, path: Path) -> list[str]:
        return ["forced problem"]


def test_verification_failures_fail_the_build(tmp_path: Path) -> None:
    layout = project(tmp_path)
    with pytest.raises(
        BookBuildError, match=r"\[demo\] cover check failed: forced problem; forced problem"
    ):
        CoverBuilder(layout, ebooks=FailingEbookVerifier()).build("demo")


def test_custom_font_directories_are_searched_before_the_bundled_fonts(tmp_path: Path) -> None:
    layout = project(tmp_path)
    empty = tmp_path / "no-fonts"
    empty.mkdir()
    assert CoverBuilder(layout, font_dirs=[empty]).build("demo").is_dir()


def pages_of(path: Path) -> int:
    return len(PdfReader(str(path)).pages)


def test_a_five_by_eight_book_gets_a_paperback_wrap_and_no_hardcover_wrap(tmp_path: Path) -> None:
    layout = project(tmp_path, 'trim_size = "5x8"\n')
    out = CoverBuilder(layout).build("demo", preview=True)
    names = sorted(p.name for p in out.iterdir())
    assert not any("hardcover" in name for name in names)
    assert "demo-paperback-wrap.pdf" in names and "demo-ebook.jpg" in names
    with Image.open(out / "demo-paperback-wrap.tif") as wrap:
        # 120 pages on white paper: 0.25 + 10 + 120 * 0.002252 in wide, 8.25 in tall, at 300 ppi.
        assert wrap.size == (3157, 2475)
    with Image.open(out / "demo-front.tif") as front:
        # Cropped on pixel boundaries, so it can differ from the idealised 5.25 in by a pixel.
        assert abs(front.size[0] - round((5 + 0.125 + 0.125) * 300)) <= 1


def test_a_cream_paper_book_gets_a_wider_spine_than_the_same_book_on_white(tmp_path: Path) -> None:
    white = tmp_path / "white"
    white.mkdir()
    cream = tmp_path / "cream"
    cream.mkdir()
    CoverBuilder(project(white)).build("demo")
    CoverBuilder(project(cream, 'paper = "cream"\n')).build("demo")
    wide = "output/covers/demo/demo-paperback-wrap.tif"
    with Image.open(white / wide) as w, Image.open(cream / wide) as c:
        # 120 pages: 0.27024 in on white and 0.3 in on cream, at 300 ppi.
        assert (w.size[0], c.size[0]) == (3757, 3765)


def test_a_five_and_a_half_by_eight_and_a_half_book_builds_every_cover_file(tmp_path: Path) -> None:
    layout = project(tmp_path, 'trim_size = "5.5x8.5"\npaper = "cream"\n')
    out = CoverBuilder(layout).build("demo")
    assert sorted(p.name for p in out.iterdir()) == sorted(f"demo-{f}" for f in FILES)
    with Image.open(out / "demo-paperback-wrap.tif") as wrap:
        # 120 cream pages: 0.25 + 11 + 120 * 0.0025 = 11.55 in = 3465 px, which rounds up by at most one.
        assert abs(wrap.size[0] - 3465) <= 1 and wrap.size[1] == 2625


@pytest.mark.parametrize("extra", ['trim_size = "7x10"\n', 'paper = "glossy"\n'])
def test_an_unknown_trim_size_or_paper_stops_the_cover_build(tmp_path: Path, extra: str) -> None:
    layout = project(tmp_path, extra)
    with pytest.raises(ManuscriptError, match="must be one of"):
        CoverBuilder(layout).build("demo")


def with_description(root: Path, trim: str, characters: int) -> ProjectLayout:
    sentence = "The keeper climbed the stairs every evening, counting the steps as her mother. "
    text = (sentence * (characters // len(sentence) + 1))[:characters].rstrip()
    paragraphs = "\\n\\n".join(text[i : i + 400] for i in range(0, len(text), 400))
    (root / "books").mkdir()
    (root / "books" / "demo.toml").write_text(
        'title = "Demo Cover"\nsubtitle = "A Subtitle"\nauthor = "Ann Author"\n'
        'publisher = "Pub House"\nauthor_bio = "Ann writes."\n'
        f'trim_size = "{trim}"\ndescription = "{paragraphs}"\n',
        encoding="utf-8",
    )
    blank_pdf(root / "output" / "demo.pdf", 120)
    return ProjectLayout(root)


def test_a_long_description_builds_at_six_by_nine_but_not_at_five_by_eight(tmp_path: Path) -> None:
    roomy = tmp_path / "roomy"
    roomy.mkdir()
    CoverBuilder(with_description(roomy, "6x9", 3000)).build("demo")
    tight = tmp_path / "tight"
    tight.mkdir()
    with pytest.raises(BackCoverTextTooLongError) as raised:
        CoverBuilder(with_description(tight, "5x8", 3000)).build("demo")
    assert raised.value.characters > raised.value.capacity > 0
    assert "does not fit above the barcode area" in str(raised.value)
    assert isinstance(raised.value, BookBuildError)
