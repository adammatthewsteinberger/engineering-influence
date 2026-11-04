"""The EPUB 3 navigation document, kept out of the reading order."""

import html

from engineering_influence.publishing.typesetting.book import Book

Entries = list[tuple[str, str, int]]


class NavDocument:
    """The toc nav (nested like the NCX) and the landmarks."""

    NAME = "nav.xhtml"

    def toc_list(self, entries: Entries) -> str:
        """The contents as a nested list: parts with their chapters inside, other matter flat.

        KDP rejects a book whose two contents lists disagree, so this nests exactly as the NCX.
        """
        out: list[str] = []
        open_part = False
        for i, (href, label, depth) in enumerate(entries):
            link = f'<a href="{html.escape(href)}">{html.escape(label, quote=False)}</a>'
            following = entries[i + 1][2] if i + 1 < len(entries) else 0
            if depth == 0:
                out.append(f"<li>{link}\n<ol>" if following == 1 else f"<li>{link}</li>")
                open_part = following == 1
            else:
                out.append(f"<li>{link}</li>")
                if following == 0 and open_part:
                    out.append("</ol></li>")
                    open_part = False
        return "\n<ol>\n" + "\n".join(out) + "\n</ol>\n"

    def render(self, entries: Entries, book: Book, toc_page: str, start_href: str) -> str:
        """Landmarks point Kindle's "Contents" at the HTML page and "Go to Beginning" at the
        first piece after it."""
        lang = book.meta.get("language", "en")
        title = html.escape(" ".join(book.meta["title"].split()), quote=False)
        return (
            "<!DOCTYPE html>\n"
            f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" '
            f'lang="{lang}" xml:lang="{lang}">\n'
            f'<head><meta charset="UTF-8" /><title>{title}</title>\n'
            '<link href="fine-ebook.css" rel="stylesheet" type="text/css" /></head>\n<body>\n'
            f'<nav epub:type="toc" id="toc">\n<h1>Contents</h1>{self.toc_list(entries)}</nav>\n'
            '<nav epub:type="landmarks" id="landmarks" hidden="hidden">\n<ol>\n'
            f'<li><a epub:type="toc" href="{html.escape(toc_page)}">Contents</a></li>\n'
            f'<li><a epub:type="bodymatter" href="{html.escape(start_href)}">Begin Reading</a></li>\n'
            "</ol>\n</nav>\n</body>\n</html>\n"
        )
