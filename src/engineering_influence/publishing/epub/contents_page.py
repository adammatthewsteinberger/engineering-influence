# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The visible HTML contents page."""

import html
import re
from collections.abc import Callable

from engineering_influence.publishing.epub.heading_ids import HeadingIds
from engineering_influence.publishing.epub.toc_labels import TocLabels
from engineering_influence.publishing.typesetting.book import Book
from engineering_influence.publishing.typesetting.manuscript_error import ManuscriptError

Entries = list[tuple[str, str, int]]


class ContentsPage:
    """Turns TeX4ht's contents page into plain linked divs, in the Kindle Publishing form."""

    NAV = re.compile(r"(<nav[^>]*epub:type=.toc.[^>]*>)(.*?)(</nav>)", re.DOTALL)
    LINK = re.compile(r"(<a href=)(['\"])([^'\"]+)\2([^>]*>)(.*?)(</a>)", re.DOTALL)

    def heading_target(self, href: str, read: Callable[[str], str]) -> str:
        """Point a contents link at its chapter's heading.

        For unnumbered chapters TeX4ht anchors the contents entry in an empty paragraph after
        the heading. Kindle's converter drops empty elements, which leaves the link without a
        target. Every chapter starts its own file, so the heading's anchor (or the top of the
        file) is the right target.
        """
        name = href.split("#", 1)[0]
        ids = HeadingIds().all(read(name))
        return f"{name}#{ids[0]}" if ids else name

    def html_toc(self, entries: Entries) -> str:
        """One linked <div> per entry, chapters indented by a CSS class, no list markup."""
        rows = [
            f'<div class="{"toc-chapter" if depth else "toc-entry"}">'
            f'<a href="{html.escape(href)}">{html.escape(label, quote=False)}</a></div>'
            for href, label, depth in entries
        ]
        return '<div class="toc">\n' + "\n".join(rows) + "\n</div>"

    def finish(self, page: str, book: Book, read: Callable[[str], str]) -> tuple[str, Entries]:
        """Return (the plain contents page, its entries).

        TeX4ht makes its contents page the EPUB navigation document as well. The Kindle
        Publishing Guidelines want the toc nav in a separate document from the HTML contents
        page, so this page keeps its heading and gets linked <div>s; the nav document is
        written separately. Entries are labelled from the book model, each link retargeted at
        its heading. ``read(name)`` returns the text of an XHTML file next to the page.
        """
        labels = TocLabels().for_book(book)
        match = self.NAV.search(page)
        if not match:
            raise ManuscriptError("tex4ebook wrote no table of contents")
        links = list(self.LINK.finditer(match.group(2)))
        if len(links) != len(labels):
            raise ManuscriptError(f"contents has {len(links)} entries, the book has {len(labels)}")
        entries = [
            (self.heading_target(link.group(3), read), label, depth)
            for link, (label, depth) in zip(links, labels, strict=True)
        ]
        return page[: match.start(1)] + self.html_toc(entries) + page[match.end(3) :], entries
