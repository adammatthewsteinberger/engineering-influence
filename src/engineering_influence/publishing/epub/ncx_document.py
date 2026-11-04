"""The NCX, matching the EPUB 3 contents exactly, for older reading systems."""

import html

from engineering_influence.publishing.typesetting.book import Book

Entries = list[tuple[str, str, int]]


class NcxDocument:
    """Parts as navPoints containing their chapters."""

    def render(self, entries: Entries, book: Book, uid: str) -> str:
        """Return the NCX XML."""
        out: list[str] = []
        open_part = False
        for order, (href, label, depth) in enumerate(entries, 1):
            point = (
                f'<navPoint id="np{order}" playOrder="{order}"><navLabel><text>'
                f"{html.escape(label, quote=False)}</text></navLabel>"
                f'<content src="{html.escape(href)}"/>'
            )
            if depth == 0:
                if open_part:
                    out.append("</navPoint>")
                out.append(point)
                open_part = True
            else:
                out.append(point + "</navPoint>")
        if open_part:
            out.append("</navPoint>")
        return (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
            f'<head><meta name="dtb:uid" content="{html.escape(uid)}"/>'
            '<meta name="dtb:depth" content="2"/><meta name="dtb:totalPageCount" content="0"/>'
            '<meta name="dtb:maxPageNumber" content="0"/></head>\n'
            f"<docTitle><text>{html.escape(book.meta['title'], quote=False)}</text></docTitle>\n"
            "<navMap>\n" + "\n".join(out) + "\n</navMap>\n</ncx>\n"
        )
