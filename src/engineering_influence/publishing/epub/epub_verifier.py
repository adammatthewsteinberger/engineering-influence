# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Checks a built EPUB against Kindle Publishing rules and against itself."""

from pathlib import Path

from engineering_influence.publishing.epub.contents_links_check import ContentsLinksCheck
from engineering_influence.publishing.epub.contents_page_check import ContentsPageCheck
from engineering_influence.publishing.epub.cover_check import CoverCheck
from engineering_influence.publishing.epub.epub_archive import EpubArchive
from engineering_influence.publishing.epub.epubcheck_runner import EpubcheckRunner
from engineering_influence.publishing.epub.internal_links_check import InternalLinksCheck
from engineering_influence.publishing.epub.nav_ncx_check import NavNcxCheck
from engineering_influence.publishing.epub.start_reading_check import StartReadingCheck
from engineering_influence.publishing.epub.stylesheet_check import StylesheetCheck
from engineering_influence.publishing.epub.text_rules_check import TextRulesCheck
from engineering_influence.publishing.epub.xml_check import XmlCheck
from engineering_influence.publishing.typesetting.book import Book


class EpubVerifier:
    """Runs the built-in checks, then epubcheck when it is installed."""

    def __init__(self, epubcheck: EpubcheckRunner | None = None) -> None:
        self._epubcheck = epubcheck or EpubcheckRunner()

    def verify(self, path: Path, book: Book) -> list[str]:
        """Return every problem found; an empty list means the EPUB passes."""
        contents = EpubArchive().read(path)
        problems: list[str] = []
        if not contents.mimetype_ok:
            problems.append("mimetype is not the first, uncompressed entry")
        problems += StylesheetCheck().run(contents)
        xml_problems, full = XmlCheck().run(contents)
        problems += xml_problems
        problems += TextRulesCheck().run(contents, book, full)
        problems += ContentsLinksCheck().run(contents, book)
        nav_problems, ncx_tree = NavNcxCheck().run(contents)
        problems += nav_problems
        problems += ContentsPageCheck().run(contents, ncx_tree)
        problems += InternalLinksCheck().run(contents)
        problems += StartReadingCheck().run(contents)
        problems += CoverCheck().run(contents)
        problems += self._epubcheck.run(path)
        return problems
