"""The Markdown dialect the print pipeline accepts."""

from markdown_it import MarkdownIt
from markdown_it.token import Token


class MarkdownParser:
    """CommonMark with smart quotes, tables, and strikethrough.

    The "replacements" rule stays off: it would turn -- into dashes, and the books use none.
    """

    def __init__(self) -> None:
        self._md = MarkdownIt("commonmark", {"typographer": True})
        self._md.enable(["smartquotes", "table", "strikethrough"])

    def parse(self, text: str) -> list[Token]:
        """Parse block-level Markdown."""
        return self._md.parse(text)

    def parse_inline(self, text: str) -> list[Token]:
        """Parse inline-only Markdown."""
        return self._md.parseInline(text)

    def render_inline(self, text: str) -> str:
        """Render inline Markdown to HTML (used to match the pages' curly quotes)."""
        return str(self._md.renderInline(text))
