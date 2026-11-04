"""End-to-end cover builds in a temporary project."""

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from PIL import Image
from pypdf import PdfWriter

from engineering_influence.publishing.covers.cover_builder import CoverBuilder
from engineering_influence.publishing.covers.cover_painter import CoverPainter
from engineering_influence.publishing.covers.cover_style import CoverStyle
from engineering_influence.publishing.covers.ebook_cover_verifier import EbookCoverVerifier
from engineering_influence.publishing.covers.painter_registry import PainterRegistry
from engineering_influence.publishing.project_layout import ProjectLayout
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError

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


class WhitePainter(CoverPainter):
    def paint(self, layout: Any, style: CoverStyle) -> Any:
        return np.ones((*reversed(layout.px), 3), np.float32)


def test_a_light_ebook_cover_gets_the_gray_border_and_still_verifies(tmp_path: Path) -> None:
    layout = project(tmp_path)
    registry = PainterRegistry()
    registry.register("white", WhitePainter())
    from engineering_influence.publishing.covers.builtin_cover_style import BuiltinCoverStyle

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


def test_verification_failures_fail_the_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    layout = project(tmp_path)
    monkeypatch.setattr(EbookCoverVerifier, "run", lambda self, path: ["forced problem"])
    with pytest.raises(
        BookBuildError, match=r"\[demo\] cover check failed: forced problem; forced problem"
    ):
        CoverBuilder(layout).build("demo")


def test_custom_font_directories_are_searched_before_the_bundled_fonts(tmp_path: Path) -> None:
    layout = project(tmp_path)
    empty = tmp_path / "no-fonts"
    empty.mkdir()
    assert CoverBuilder(layout, font_dirs=[empty]).build("demo").is_dir()
