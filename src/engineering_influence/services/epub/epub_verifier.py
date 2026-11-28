# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Checks a built EPUB against Kindle Publishing rules and against itself."""

from pathlib import Path

from engineering_influence.interfaces.epub_archive_reader_interface import (
    EpubArchiveReaderInterface,
)
from engineering_influence.interfaces.epub_cover_inspector_interface import (
    EpubCoverInspectorInterface,
)
from engineering_influence.interfaces.epub_verifier_interface import EpubVerifierInterface
from engineering_influence.interfaces.epubcheck_interface import EpubcheckInterface
from engineering_influence.models.typesetting.book import Book
from engineering_influence.models.typesetting.text_policy import TextPolicy
from engineering_influence.services.epub.contents_links_check import ContentsLinksCheck
from engineering_influence.services.epub.contents_page_check import ContentsPageCheck
from engineering_influence.services.epub.cover_check import CoverCheck
from engineering_influence.services.epub.internal_links_check import InternalLinksCheck
from engineering_influence.services.epub.nav_ncx_check import NavNcxCheck
from engineering_influence.services.epub.start_reading_check import StartReadingCheck
from engineering_influence.services.epub.stylesheet_check import StylesheetCheck
from engineering_influence.services.epub.text_rules_check import TextRulesCheck
from engineering_influence.services.epub.xml_check import XmlCheck


class EpubVerifier(EpubVerifierInterface):
    """Runs the built-in checks, then epubcheck when it is installed."""

    def __init__(
        self,
        archive: EpubArchiveReaderInterface,
        epubcheck: EpubcheckInterface,
        cover_inspector: EpubCoverInspectorInterface,
    ) -> None:
        """Remember the archive reader, epubcheck and cover inspector used to verify an EPUB."""
        self._archive = archive
        self._epubcheck = epubcheck
        self._cover_inspector = cover_inspector

    def verify(self, path: Path, book: Book) -> list[str]:
        """Return every problem found; an empty list means the EPUB passes."""
        contents = self._archive.read(path)
        problems: list[str] = []
        if not contents.mimetype_ok:
            problems.append("mimetype is not the first, uncompressed entry")
        problems += StylesheetCheck().run(contents)
        xml_problems, full = XmlCheck().run(contents)
        problems += xml_problems
        policy = TextPolicy.for_name(book.meta.get("kind"))
        problems += TextRulesCheck().run(contents, book, full, policy)
        problems += ContentsLinksCheck().run(contents, book)
        nav_problems, ncx_tree = NavNcxCheck().run(contents)
        problems += nav_problems
        problems += ContentsPageCheck().run(contents, ncx_tree)
        problems += InternalLinksCheck().run(contents)
        problems += StartReadingCheck().run(contents)
        problems += CoverCheck(self._cover_inspector).run(contents)
        problems += self._epubcheck.run(path)
        return problems
