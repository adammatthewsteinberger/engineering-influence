# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The members of an EPUB 3 that holds a screenplay as one page: the container, the package, the navigation, the page and its style."""

from html import escape
from typing import ClassVar

from engineering_influence.models.fountain_block import FountainBlock
from engineering_influence.services.interfaces.fountain_parser_interface import (
    FountainParserInterface,
)
from engineering_influence.services.interfaces.screenplay_epub_package_interface import (
    ScreenplayEpubPackageInterface,
)


class ScreenplayEpubPackage(ScreenplayEpubPackageInterface):
    """The mimetype entry comes first and is stored, as the EPUB format requires; the rest are deflated.

    The page is one XHTML document: the title page, then the elements, each a paragraph whose class names its kind
    (so the style can indent it the way the printed page does). Dates are fixed, so the same script always gives the
    same archive. Every value taken from the script is escaped.
    """

    MODIFIED: ClassVar[str] = "2000-01-01T00:00:00Z"
    IDENTIFIER_PREFIX: ClassVar[str] = "urn:engineering-influence:screenplay:"
    PAGE: ClassVar[str] = "OEBPS/screenplay.xhtml"
    PACKAGE: ClassVar[str] = "OEBPS/content.opf"
    STYLE: ClassVar[str] = "OEBPS/style.css"
    NAV: ClassVar[str] = "OEBPS/nav.xhtml"
    STYLESHEET: ClassVar[str] = (
        "body { font-family: monospace; font-size: 1em; margin: 0 6%; }\n"
        ".title { text-align: center; margin-top: 30%; }\n"
        "p { margin: 0 0 1em 0; }\n"
        ".heading { font-weight: bold; text-transform: uppercase; }\n"
        ".scene-number { float: right; }\n"
        ".transition { text-align: right; }\n"
        ".centered { text-align: center; }\n"
        ".cue { margin-left: 35%; }\n"
        ".dialogue { margin-left: 15%; margin-right: 25%; }\n"
        ".parenthetical { margin-left: 25%; margin-right: 35%; }\n"
    )

    def __init__(self, parser: FountainParserInterface) -> None:
        self._parser = parser

    def entries(self, script: str) -> tuple[tuple[str, bytes, bool], ...]:
        """The archive's members in order, as (name, data, stored)."""
        title = self._title(script)
        identifier = f"{self.IDENTIFIER_PREFIX}{self._slug(title)}"
        return (
            ("mimetype", b"application/epub+zip", True),
            ("META-INF/container.xml", self._container().encode("utf-8"), False),
            (self.PACKAGE, self._package(title, identifier).encode("utf-8"), False),
            (self.NAV, self._nav(title).encode("utf-8"), False),
            (self.PAGE, self._page(script, title).encode("utf-8"), False),
            (self.STYLE, self.STYLESHEET.encode("utf-8"), False),
        )

    def _title(self, script: str) -> str:
        for key, value in self._parser.title_page(script):
            if key.lower() == "title" and value.strip():
                return value.strip()
        return "Untitled screenplay"

    @staticmethod
    def _slug(title: str) -> str:
        return (
            "-".join("".join(c.lower() if c.isalnum() else " " for c in title).split())
            or "untitled"
        )

    def _container(self) -> str:
        return (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">\n'
            '  <rootfiles><rootfile full-path="OEBPS/content.opf" '
            'media-type="application/oebps-package+xml"/></rootfiles>\n'
            "</container>\n"
        )

    def _package(self, title: str, identifier: str) -> str:
        return (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="book-id">\n'
            '  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">\n'
            f'    <dc:identifier id="book-id">{escape(identifier)}</dc:identifier>\n'
            f"    <dc:title>{escape(title)}</dc:title>\n"
            "    <dc:language>en</dc:language>\n"
            f'    <meta property="dcterms:modified">{self.MODIFIED}</meta>\n'
            "  </metadata>\n"
            "  <manifest>\n"
            '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>\n'
            '    <item id="page" href="screenplay.xhtml" media-type="application/xhtml+xml"/>\n'
            '    <item id="style" href="style.css" media-type="text/css"/>\n'
            "  </manifest>\n"
            '  <spine><itemref idref="page"/></spine>\n'
            "</package>\n"
        )

    def _nav(self, title: str) -> str:
        return (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">\n'
            f"<head><title>{escape(title)}</title></head>\n"
            "<body>\n"
            '<nav epub:type="toc"><ol>\n'
            f'  <li><a href="screenplay.xhtml">{escape(title)}</a></li>\n'
            "</ol></nav>\n"
            "</body>\n</html>\n"
        )

    def _block(self, block: FountainBlock) -> str:
        """One element as a paragraph; a heading's locked scene number is floated to the right."""
        if block.kind != "heading":
            return f'<p class="{block.kind}">{"<br/>".join(escape(line) for line in block.lines)}</p>\n'
        plain, number = self._parser.split_scene_number(" ".join(block.lines))
        label = "" if number is None else f'<span class="scene-number">{escape(number)}</span>'
        return f'<p class="heading">{escape(plain)}{label}</p>\n'

    def _page(self, script: str, title: str) -> str:
        pairs = "".join(
            f'<p class="title">{escape(key)}: {escape(value)}</p>\n'
            for key, value in self._parser.title_page(script)
        )
        body = "".join(self._block(block) for block in self._parser.blocks(script))
        return (
            '<?xml version="1.0" encoding="utf-8"?>\n'
            '<html xmlns="http://www.w3.org/1999/xhtml">\n'
            f"<head><title>{escape(title)}</title>"
            '<link rel="stylesheet" type="text/css" href="style.css"/></head>\n'
            f"<body>\n{pairs}{body}</body>\n</html>\n"
        )
