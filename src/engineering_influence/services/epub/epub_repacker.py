# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Rewrites a tex4ebook EPUB into the finished, deterministic package."""

import datetime as dt
import re
from collections.abc import Iterator
from pathlib import Path

from engineering_influence.interfaces.ebook_cover_interface import EbookCoverInterface
from engineering_influence.interfaces.epub_package_interface import EpubPackageInterface
from engineering_influence.models.epub.cover_declaration import CoverDeclaration
from engineering_influence.models.epub.xhtml_patterns import XhtmlPatterns
from engineering_influence.models.typesetting.book import Book
from engineering_influence.services.epub.contents_page import ContentsPage
from engineering_influence.services.epub.css_cleaner import CssCleaner
from engineering_influence.services.epub.epub_identifier import EpubIdentifier
from engineering_influence.services.epub.interfaces.epub_repacker_interface import (
    EpubRepackerInterface,
)
from engineering_influence.services.epub.nav_document import NavDocument
from engineering_influence.services.epub.ncx_document import NcxDocument
from engineering_influence.services.epub.opf_editor import OpfEditor
from engineering_influence.services.epub.xhtml_cleaner import XhtmlCleaner


class EpubRepacker(EpubRepackerInterface):
    """Copies the EPUB with the finished OPF, nav, NCX, and XHTML.

    The mimetype entry stays first and stored, and every member carries a stable timestamp
    instead of the wall clock.
    """

    def __init__(
        self,
        cover: EbookCoverInterface,
        package: EpubPackageInterface,
        identifier: EpubIdentifier,
    ) -> None:
        self._cover = cover
        self._package = package
        self._identifier = identifier

    def zip_stamp(self, book: Book) -> tuple[int, int, int, int, int, int]:
        """A publication-year midnight: stable, and valid (ZIP cannot represent pre-1980)."""
        stamp = dt.datetime(int(book.meta.get("year", 2026)), 1, 1, 0, 0, 0)
        return (stamp.year, stamp.month, stamp.day, stamp.hour, stamp.minute, stamp.second)

    def repack(self, epub: Path, book: Book, out: Path) -> None:
        """Write the finished EPUB to out."""
        files = self._package.read_members(epub)
        opf_name = next(name for name in files if name.endswith(".opf"))
        opf = files[opf_name].decode("utf-8")
        base = opf_name.rsplit("/", 1)[0] + "/" if "/" in opf_name else ""
        nav_item = XhtmlPatterns.NAV_ITEM.search(opf)
        ncx_item = re.search(r"<item\b(?=[^>]*application/x-dtbncx\+xml)[^>]*href=.([^'\"]+)", opf)
        if nav_item is None or ncx_item is None:
            raise ValueError("the tex4ebook package has no navigation document or NCX")
        # TeX4ht's navigation document is its contents page, which stays in the spine.
        toc_page = nav_item.group(1)
        page, entries = ContentsPage().finish(
            files[base + toc_page].decode("utf-8"),
            book,
            lambda name: files[base + name].decode("utf-8"),
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
        xhtml, css = XhtmlCleaner(), CssCleaner()

        def members() -> Iterator[tuple[str, bytes, bool]]:
            # Lazy on purpose: the navigation page and the cover are produced only once the
            # package is open and the members before them are written.
            for name, original in files.items():
                data = replaced[name].encode("utf-8") if name in replaced else original
                if name.endswith(".xhtml"):
                    data = xhtml.clean(data.decode("utf-8")).encode("utf-8")
                elif name.endswith(".css"):
                    data = css.strip_hidden_rules(data.decode("utf-8")).encode("utf-8")
                yield name, data, name == "mimetype"
            nav = NavDocument().render(entries, book, toc_page, start_href)
            yield base + NavDocument.NAME, xhtml.clean(nav).encode("utf-8"), False
            yield base + CoverDeclaration.NAME, self._cover.jpeg(book), True

        self._package.write_members(out, members(), self.zip_stamp(book))
