"""Edits the package document (OPF) that tex4ebook writes."""

import html
import re

from engineering_influence.publishing.epub.cover_image import CoverImage
from engineering_influence.publishing.epub.nav_document import NavDocument
from engineering_influence.publishing.typesetting.book import Book


class OpfEditor:
    """Adds store metadata, the separate nav document, the guide, and the cover."""

    def finish(self, opf: str, book: Book) -> str:
        """Add store metadata and normalize every publication date to the release year.

        TeX4ebook emits ``dcterms:modified`` from the wall clock. Leaving that value in the OPF
        makes an otherwise identical EPUB change on every build.
        """
        m = book.meta

        def esc(s: str) -> str:
            return html.escape(" ".join(s.split()), quote=False)

        year = m.get("year", 2026)
        extra = [
            f"<dc:publisher>{esc(m['publisher'])}</dc:publisher>",
            (
                f"<dc:rights>Copyright © {year} {esc(m['publisher'])}. "
                "All rights reserved.</dc:rights>"
            ),
        ]
        if m.get("subtitle"):
            extra += [
                f'<dc:title id="subtitle">{esc(m["subtitle"])}</dc:title>',
                '<meta refines="#subtitle" property="title-type">subtitle</meta>',
            ]
        if m.get("description"):
            extra.append(f"<dc:description>{esc(m['description'])}</dc:description>")
        extra += [
            '<meta property="schema:accessMode">textual</meta>',
            '<meta property="schema:accessModeSufficient">textual</meta>',
            '<meta property="schema:accessibilityFeature">structuralNavigation</meta>',
            '<meta property="schema:accessibilityFeature">tableOfContents</meta>',
            '<meta property="schema:accessibilityFeature">readingOrder</meta>',
            '<meta property="schema:accessibilityHazard">none</meta>',
            (
                '<meta property="schema:accessibilitySummary">Reflowable text with a navigable '
                "table of contents and semantic headings. The only image is the cover.</meta>"
            ),
        ]
        opf = re.sub(r"<dc:date>[^<]*</dc:date>", f"<dc:date>{year}</dc:date>", opf)
        opf = re.sub(
            r"(<meta\b[^>]*property=['\"]dcterms:modified['\"][^>]*>)[^<]*(</meta>)",
            rf"\g<1>{year}-01-01T00:00:00Z\g<2>",
            opf,
        )
        opf = opf.replace("<dc:title>", '<dc:title id="title">', 1)
        extra.insert(0, '<meta refines="#title" property="title-type">main</meta>')
        return opf.replace("</metadata>", "\n".join(extra) + "\n</metadata>", 1)

    def move_nav(self, opf: str, toc_page: str) -> str:
        """Make nav.xhtml the navigation document, outside the spine; the contents page stays."""
        opf = re.sub(
            rf"(<item\b(?=[^>]*href=.{re.escape(toc_page)}.)[^>]*?)\s+properties=.nav.",
            r"\1",
            opf,
            count=1,
        )
        item = (
            f'<item href="{NavDocument.NAME}" id="nav" media-type="application/xhtml+xml" '
            'properties="nav"></item>'
        )
        return opf.replace("</manifest>", item + "\n</manifest>", 1)

    def add_guide(self, opf: str, nav_href: str, start_href: str) -> str:
        """The EPUB 2 guide, which older Kindle conversions still read for the same two places."""
        guide = (
            "<guide>\n"
            f'<reference type="toc" title="Contents" href="{html.escape(nav_href)}"/>\n'
            f'<reference type="text" title="Begin Reading" href="{html.escape(start_href)}"/>\n'
            "</guide>\n"
        )
        return opf.replace("</package>", guide + "</package>", 1)

    def add_cover(self, opf: str) -> str:
        """Declare the cover both ways the Kindle Publishing Guidelines accept."""
        item = (
            f'<item href="{CoverImage.NAME}" id="{CoverImage.ID}" media-type="image/jpeg" '
            'properties="cover-image"></item>'
        )
        opf = opf.replace("</manifest>", item + "\n</manifest>", 1)
        return opf.replace(
            "</metadata>", f'<meta name="cover" content="{CoverImage.ID}"/>\n</metadata>', 1
        )
