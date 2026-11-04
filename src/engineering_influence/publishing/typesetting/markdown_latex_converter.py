# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A chapter body in Markdown to LaTeX, including callout and illustration blocks."""

import re

from engineering_influence.publishing.typesetting.block_renderer import BlockRenderer
from engineering_influence.publishing.typesetting.markdown_parser import MarkdownParser


class MarkdownLatexConverter:
    """Converts a chapter body (without its title) to LaTeX."""

    CALLOUT = re.compile(r"^\[CALLOUT\]\n(.*?)\n\[/CALLOUT\]$", re.DOTALL | re.MULTILINE)
    ILLUSTRATION = re.compile(
        r"^\[ILLUSTRATION\]\n(.*?)\n\[/ILLUSTRATION\]$", re.DOTALL | re.MULTILINE
    )

    def __init__(self) -> None:
        self._parser = MarkdownParser()

    def convert(self, body: str, *, style: str) -> str:
        """Return the LaTeX for the body in the given chapter style."""
        pieces: list[str] = []
        pos = 0
        renderer = BlockRenderer(style)
        pattern = re.compile(
            self.CALLOUT.pattern + "|" + self.ILLUSTRATION.pattern, re.DOTALL | re.MULTILINE
        )
        for match in pattern.finditer(body):
            pieces.append(renderer.render(self._parser.parse(body[pos : match.start()])))
            if match.group(1) is not None:
                pieces.append(self._block("callout", match.group(1)))
            else:
                pieces.append(self._block("illustration", match.group(2)))
            renderer.first_paragraph_pending = False
            pos = match.end()
        pieces.append(renderer.render(self._parser.parse(body[pos:])))
        latex = "".join(pieces)
        if style == "references":
            latex = "\\begin{referencelist}\n" + latex + "\n\\end{referencelist}\n"
        return latex

    def _block(self, environment: str, content: str) -> str:
        inner = BlockRenderer("plain").render(self._parser.parse(content))
        return f"\n\\begin{{{environment}}}\n{inner.strip()}\n\\end{{{environment}}}\n"
