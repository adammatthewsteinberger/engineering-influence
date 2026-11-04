"""The bundled LaTeX assets are complete, licensed, and usable by the builder."""

import re
from pathlib import Path

from engineering_influence.publishing.package_assets import PackageAssets
from engineering_influence.publishing.project_layout import ProjectLayout
from engineering_influence.publishing.typesetting.book_builder import BookBuilder

EXPECTED = {
    "fine-book.cls",
    "fine-book-hardcover.cls",
    "fine-ebook.sty",
    "fine-ebook.cfg",
    "fine-ebook.css",
}


def test_assets_contain_classes_stylesheet_and_fonts() -> None:
    with PackageAssets().directory() as assets:
        assert EXPECTED <= {p.name for p in assets.iterdir()}
        assert (assets / "fonts" / "README.md").is_file()


def test_every_font_the_class_names_is_shipped() -> None:
    with PackageAssets().directory() as assets:
        source = (assets / "fine-book.cls").read_text(encoding="utf-8")
        names = set(
            re.findall(r"(EBGaramond-[A-Za-z]+|LibertinusSerif-Regular|DejaVuSerif)", source)
        )
        shipped = {p.stem for p in (assets / "fonts").iterdir()}
        assert names and names <= shipped, sorted(names - shipped)


def test_every_font_family_ships_its_license() -> None:
    with PackageAssets().directory() as assets:
        fonts = {p.name for p in (assets / "fonts").iterdir()}
    assert {"OFL-EBGaramond.txt", "OFL-Libertinus.txt", "LICENSE-DejaVu.txt"} <= fonts
    assert any(name.startswith("EBGaramond") and name.endswith(".otf") for name in fonts)


def test_builder_defaults_to_the_bundled_assets(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.md").write_text("# Chapter 1: One\n\nOne begins here.\n", "utf-8")
    (tmp_path / "books").mkdir()
    (tmp_path / "books" / "demo.toml").write_text(
        'source = "src"\ntitle = "T"\nauthor = "A"\npublisher = "P"\nedition = "First Edition"\n'
        'author_bio = "Bio."\nparts = [{ title = "One", chapters = ["a.md"] }]\n',
        encoding="utf-8",
    )
    tex = BookBuilder(ProjectLayout(tmp_path)).build("demo", tex_only=True, hardcover=True)
    workdir = tex.parent
    assert (workdir / "fine-book.cls").is_file() and (workdir / "fine-book-hardcover.cls").is_file()
    assert (workdir / "fonts" / "EBGaramond-Regular.otf").is_file()
