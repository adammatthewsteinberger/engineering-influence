"""Metadata strings rendered as LaTeX."""

from engineering_influence.publishing.typesetting.inline_renderer import InlineRenderer
from engineering_influence.publishing.typesetting.markdown_parser import MarkdownParser


class TexText:
    """Escapes plain metadata, keeping line breaks."""

    def __init__(self) -> None:
        self._parser = MarkdownParser()
        self._inline = InlineRenderer()

    def text(self, s: str) -> str:
        """Render one metadata string."""
        rendered = self._inline.inline(self._parser.parse_inline(s)[0].children or [])
        return rendered.replace("\n", "\\\\\n")

    def paragraphs(self, s: str) -> str:
        """Render blank-line separated paragraphs."""
        return "\n\n".join(self.text(p.strip()) for p in s.strip().split("\n\n"))
