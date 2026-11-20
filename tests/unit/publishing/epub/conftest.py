"""Fixtures: a small book, a fake tex4ebook EPUB, and the finished EPUB built from it."""

import io
import re
import zipfile
from collections.abc import Callable
from pathlib import Path

import pytest
from PIL import Image

from engineering_influence.infrastructure.epub.cover_image import CoverImage
from engineering_influence.infrastructure.epub.epub_archive import EpubArchive
from engineering_influence.infrastructure.epub.epub_cover_inspector import EpubCoverInspector
from engineering_influence.infrastructure.epub.epubcheck_runner import EpubcheckRunner
from engineering_influence.infrastructure.epub.tex4ebook_compiler import Tex4ebookCompiler
from engineering_influence.infrastructure.epub.zip_epub_package import ZipEpubPackage
from engineering_influence.infrastructure.publishing.filesystem_manuscript_source import (
    FilesystemManuscriptSource,
)
from engineering_influence.infrastructure.publishing.package_assets import PackageAssets
from engineering_influence.infrastructure.typesetting.filesystem_build_workspace import (
    FilesystemBuildWorkspace,
)
from engineering_influence.interfaces.epub_compiler_interface import EpubCompilerInterface
from engineering_influence.interfaces.epubcheck_interface import EpubcheckInterface
from engineering_influence.models.publishing.project_layout import ProjectLayout
from engineering_influence.models.typesetting.book import Book
from engineering_influence.models.typesetting.chapter import Chapter
from engineering_influence.repositories.typesetting.book_loader import BookLoader
from engineering_influence.services.epub.epub_builder import EpubBuilder
from engineering_influence.services.epub.epub_identifier import EpubIdentifier
from engineering_influence.services.epub.epub_repacker import EpubRepacker
from engineering_influence.services.epub.epub_verifier import EpubVerifier

PAGE = (
    "<?xml version='1.0' encoding='utf-8'?>\n<!DOCTYPE html>\n"
    '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="en">'
    "<head><title>T</title></head><body>{body}</body></html>"
)


def page(body: str) -> str:
    return PAGE.format(body=body)


def make_verifier(epubcheck: EpubcheckInterface | None = None) -> EpubVerifier:
    """The verifier wired with the real archive reader and cover inspector."""
    return EpubVerifier(EpubArchive(), epubcheck or EpubcheckRunner(), EpubCoverInspector())


def make_repacker(layout: ProjectLayout, identifier: EpubIdentifier | None = None) -> EpubRepacker:
    """The repacker wired with the real cover image and zip package."""
    return EpubRepacker(CoverImage(layout), ZipEpubPackage(), identifier or EpubIdentifier())


def make_epub_builder(
    layout: ProjectLayout,
    compiler: EpubCompilerInterface | None = None,
    assets: Path | None = None,
) -> EpubBuilder:
    """The ebook builder wired with the real loader, workspace, assets and repacker."""
    identifier = EpubIdentifier()
    return EpubBuilder(
        layout,
        BookLoader(layout.root),
        compiler or Tex4ebookCompiler(),
        FilesystemBuildWorkspace(),
        PackageAssets(assets),
        make_repacker(layout, identifier),
        FilesystemManuscriptSource(),
        identifier,
    )


def make_book() -> Book:
    def chapter(kind: str, title: str, number: int | None = None) -> Chapter:
        return Chapter(Path(f"{title}.md"), kind, title=title, short=title, number=number)

    return Book(
        "demo",
        {
            "title": "Demo Book",
            "subtitle": "A Subtitle",
            "author": "Ann Author",
            "publisher": "Pub House",
            "edition": "First Edition",
            "description": "About the demo.",
            "year": 2031,
        },
        front=[chapter("front", "Foreword")],
        parts=[("The Start", [chapter("chapter", "One", 1), chapter("chapter", "Two", 2)])],
        back=[chapter("back", "Notes")],
    )


@pytest.fixture
def book() -> Book:
    return make_book()


@pytest.fixture
def layout(tmp_path: Path) -> ProjectLayout:
    cover_dir = tmp_path / "output" / "covers" / "demo"
    cover_dir.mkdir(parents=True)
    Image.new("RGB", (1600, 2500), "navy").save(cover_dir / "demo-ebook.jpg", "JPEG")
    return ProjectLayout(tmp_path)


# file name, heading id, heading text, body text
RAW_PAGES = [
    ("fore.xhtml", "h1", "Foreword", "A foreword. This is the First Edition."),
    ("part.xhtml", "h2", "The Start", "Part page."),
    ("c1.xhtml", "h3", "One", "Chapter one text."),
    ("c2.xhtml", "h4", "Two", "Chapter two text."),
    ("notes.xhtml", "h5", "Notes", "Some notes."),
    ("about.xhtml", "h6", "About the Author", "Ann writes."),
]


def raw_epub(path: Path) -> Path:
    """What tex4ebook leaves behind, with the defects the repacker exists to remove."""
    links = "".join(
        f"<li><a href='{name}#{hid}'>{title}</a></li>" for name, hid, title, _ in RAW_PAGES
    )
    toc = page(f"<nav epub:type='toc' id='tableofcontents'><h2>Contents</h2><ol>{links}</ol></nav>")
    items = "".join(
        f'<item href="{n}" id="p{i}" media-type="application/xhtml+xml"></item>'
        for i, (n, *_rest) in enumerate(RAW_PAGES)
    )
    refs = "".join(f'<itemref idref="p{i}"/>' for i in range(len(RAW_PAGES)))
    opf = (
        '<?xml version="1.0"?>\n<package xmlns="http://www.idpf.org/2007/opf" version="3.0" '
        'unique-identifier="uid"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/">'
        "<dc:title>Demo Book</dc:title><dc:date>2020-01-01</dc:date>"
        '<meta property="dcterms:modified">2020-05-05T05:05:05Z</meta></metadata><manifest>'
        '<item href="toc.xhtml" id="toc" media-type="application/xhtml+xml" properties="nav"></item>'
        '<item href="demo.ncx" id="ncx" media-type="application/x-dtbncx+xml"></item>'
        '<item href="demo.css" id="css" media-type="text/css"></item>'
        f'{items}</manifest><spine toc="ncx"><itemref idref="toc"/>{refs}</spine></package>'
    )
    members: dict[str, str] = {
        "mimetype": "application/epub+zip",
        "META-INF/container.xml": "<container/>",
        "OEBPS/demo.opf": opf,
        "OEBPS/toc.xhtml": toc,
        "OEBPS/demo.ncx": "<ncx/>",
        "OEBPS/demo.css": "body { margin: 0 }\nh2 br { display: none }\np { margin: 0 }\n",
    }
    for name, hid, title, text in RAW_PAGES:
        members[f"OEBPS/{name}"] = page(
            f"<h2 class='chapterHead'><a id='{hid}'></a>{title}</h2><p>{text}</p><p> </p>"
        )
    with zipfile.ZipFile(path, "w") as z:
        for name, data in members.items():
            kind = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED
            z.writestr(name, data, compress_type=kind)
    return path


@pytest.fixture
def raw(tmp_path: Path) -> Path:
    return raw_epub(tmp_path / "raw.epub")


@pytest.fixture
def finished(tmp_path: Path, raw: Path, book: Book, layout: ProjectLayout) -> Path:
    out = tmp_path / "finished.epub"
    make_repacker(layout).repack(raw, book, out)
    return out


Edit = Callable[[str], str]


@pytest.fixture
def rewrite(tmp_path: Path) -> Callable[..., Path]:
    """Copy an EPUB, editing members (by name suffix), dropping some, or replacing bytes."""
    counter = iter(range(1000))

    def run(
        src: Path,
        edits: dict[str, Edit] | None = None,
        drop: tuple[str, ...] = (),
        replace: dict[str, bytes] | None = None,
        first: str | None = None,
    ) -> Path:
        out = tmp_path / f"mutant{next(counter)}.epub"
        with zipfile.ZipFile(src) as z:
            members = [(i, z.read(i.filename)) for i in z.infolist()]
        if first:
            members.insert(0, (zipfile.ZipInfo(first), b"x"))
        with zipfile.ZipFile(out, "w") as dst:
            for info, data in members:
                name = info.filename
                if any(name.endswith(d) for d in drop):
                    continue
                for suffix, fn in (edits or {}).items():
                    if name.endswith(suffix):
                        data = fn(data.decode("utf-8")).encode("utf-8")
                for suffix, new in (replace or {}).items():
                    if name.endswith(suffix):
                        data = new
                kind = info.compress_type if name != "mimetype" else zipfile.ZIP_STORED
                dst.writestr(zipfile.ZipInfo(name, date_time=(2031, 1, 1, 0, 0, 0)), data, kind)
        return out

    return run


def jpeg_bytes(size: tuple[int, int], mode: str = "RGB", fmt: str = "JPEG") -> bytes:
    buffer = io.BytesIO()
    Image.new(mode, size).save(buffer, format=fmt)
    return buffer.getvalue()


def regex_sub(pattern: str, repl: str, count: int = 0) -> Edit:
    return lambda s: re.sub(pattern, repl, s, count=count, flags=re.DOTALL)
