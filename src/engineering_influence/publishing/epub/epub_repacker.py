"""Rewrites a tex4ebook EPUB into the finished, deterministic package."""

import datetime as dt
import re
import zipfile
from pathlib import Path

from engineering_influence.publishing.epub.contents_page import ContentsPage
from engineering_influence.publishing.epub.cover_image import CoverImage
from engineering_influence.publishing.epub.css_cleaner import CssCleaner
from engineering_influence.publishing.epub.epub_identifier import EpubIdentifier
from engineering_influence.publishing.epub.nav_document import NavDocument
from engineering_influence.publishing.epub.ncx_document import NcxDocument
from engineering_influence.publishing.epub.opf_editor import OpfEditor
from engineering_influence.publishing.epub.xhtml_cleaner import XhtmlCleaner
from engineering_influence.publishing.epub.xhtml_patterns import XhtmlPatterns
from engineering_influence.publishing.typesetting.book import Book


class EpubRepacker:
    """Copies the EPUB with the finished OPF, nav, NCX, and XHTML.

    The mimetype entry stays first and stored, and every member carries a stable timestamp
    instead of the wall clock.
    """

    def __init__(self, cover: CoverImage, identifier: EpubIdentifier | None = None) -> None:
        self._cover = cover
        self._identifier = identifier or EpubIdentifier()

    def zip_stamp(self, book: Book) -> tuple[int, int, int, int, int, int]:
        """A publication-year midnight: stable, and valid (ZIP cannot represent pre-1980)."""
        stamp = dt.datetime(int(book.meta.get("year", 2026)), 1, 1, 0, 0, 0)
        return (stamp.year, stamp.month, stamp.day, stamp.hour, stamp.minute, stamp.second)

    def repack(self, epub: Path, book: Book, out: Path) -> None:
        """Write the finished EPUB to out."""
        with zipfile.ZipFile(epub) as src:
            files = {i.filename: (i, src.read(i.filename)) for i in src.infolist()}
        opf_name = next(name for name in files if name.endswith(".opf"))
        opf = files[opf_name][1].decode("utf-8")
        base = opf_name.rsplit("/", 1)[0] + "/" if "/" in opf_name else ""
        nav_item = XhtmlPatterns.NAV_ITEM.search(opf)
        ncx_item = re.search(r"<item\b(?=[^>]*application/x-dtbncx\+xml)[^>]*href=.([^'\"]+)", opf)
        if nav_item is None or ncx_item is None:
            raise ValueError("the tex4ebook package has no navigation document or NCX")
        # TeX4ht's navigation document is its contents page, which stays in the spine.
        toc_page = nav_item.group(1)
        page, entries = ContentsPage().finish(
            files[base + toc_page][1].decode("utf-8"),
            book,
            lambda name: files[base + name][1].decode("utf-8"),
        )
        start_href = entries[0][0]  # reading starts at the first piece after the contents
        editor = OpfEditor()
        opf = editor.move_nav(
            editor.add_cover(editor.add_guide(editor.finish(opf, book), toc_page, start_href)),
            toc_page,
        )
        uid = self._identifier.of(book)[0]
        replaced = {
            opf_name: opf,
            base + toc_page: page,
            base + ncx_item.group(1): NcxDocument().render(entries, book, uid),
        }
        stamp = self.zip_stamp(book)
        xhtml, css = XhtmlCleaner(), CssCleaner()
        with zipfile.ZipFile(out, "w") as dst:
            for name, (_info, data) in files.items():
                if name in replaced:
                    data = replaced[name].encode("utf-8")
                if name.endswith(".xhtml"):
                    data = xhtml.clean(data.decode("utf-8")).encode("utf-8")
                elif name.endswith(".css"):
                    data = css.strip_hidden_rules(data.decode("utf-8")).encode("utf-8")
                kind = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED
                dst.writestr(zipfile.ZipInfo(name, date_time=stamp), data, compress_type=kind)
            nav = NavDocument().render(entries, book, toc_page, start_href)
            dst.writestr(
                zipfile.ZipInfo(base + NavDocument.NAME, date_time=stamp),
                xhtml.clean(nav).encode("utf-8"),
                compress_type=zipfile.ZIP_DEFLATED,
            )
            dst.writestr(
                zipfile.ZipInfo(base + CoverImage.NAME, date_time=stamp),
                self._cover.jpeg(book),
                compress_type=zipfile.ZIP_STORED,
            )
