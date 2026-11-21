# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Metadata strings rendered as LaTeX."""

import re

from engineering_influence.errors.typesetting.manuscript_error import ManuscriptError
from engineering_influence.services.typesetting.inline_renderer import InlineRenderer
from engineering_influence.services.typesetting.interfaces.tex_text_interface import (
    TexTextInterface,
)
from engineering_influence.services.typesetting.latex_escaper import LatexEscaper
from engineering_influence.services.typesetting.markdown_parser import MarkdownParser


class TexText(TexTextInterface):
    """Escapes plain metadata, keeping line breaks."""

    # A web address is an http(s) URL, or a bare host name with an optional path (pub.example,
    # www.pub.example/about). Nothing with a colon before the first slash is accepted but
    # http(s): that rules out every other scheme, and "host:port" with it, because "a:0/b" is
    # also how a script URL looks. A port is written with its scheme (https://pub.example:8080).
    WEB_ADDRESS = re.compile(r"(?i)https?://\S+|[A-Za-z0-9.-]+(?:[/?#]\S*)?")

    # TeX would act on these in the PDF info string, so none of them can be carried into it.
    PDF_INFO_UNSAFE = re.compile(r"[\\{}%#^~\x00-\x1f\x7f]")

    def __init__(self) -> None:
        self._parser = MarkdownParser()
        self._inline = InlineRenderer()
        self._escaper = LatexEscaper()

    def text(self, s: str) -> str:
        """Render one metadata string."""
        rendered = self._inline.inline(self._parser.parse_inline(s)[0].children or [])
        return rendered.replace("\n", "\\\\\n")

    def paragraphs(self, s: str) -> str:
        """Render blank-line separated paragraphs."""
        return "\n\n".join(self.text(p.strip()) for p in s.strip().split("\n\n"))

    def url(self, s: str) -> str:
        """A URL or mail address safe inside \\url{} and \\href{}."""
        return self._escaper.url(s.strip())

    def web_url(self, s: str) -> str:
        """A web address safe inside \\url{}, accepting only http(s) or a bare host name.

        A link with another scheme, such as ``javascript:``, would be clickable in an ebook.
        """
        text = s.strip()
        if not self.WEB_ADDRESS.fullmatch(text):
            raise ManuscriptError(
                "a website must be an http or https address (https://pub.example) or a bare "
                "host name (pub.example); write a port with its scheme"
            )
        return self.url(text)

    def pdf_info(self, s: str) -> str:
        """A string safe inside the PDF info dictionary's ``( )`` after TeX has expanded it.

        TeX would act on a backslash, brace, ``%``, ``#``, ``^`` or ``~``, and a stray
        parenthesis would end the PDF string and let the rest become dictionary entries, so
        those are dropped, as is any unbalanced parenthesis. Ordinary titles are unchanged.
        """
        cleaned = self.PDF_INFO_UNSAFE.sub("", re.sub(r"[\r\n\t]+", " ", s))
        open_at: list[int] = []
        unmatched: set[int] = set()
        for index, char in enumerate(cleaned):
            if char == "(":
                open_at.append(index)
            elif char == ")":
                if open_at:
                    open_at.pop()
                else:
                    unmatched.add(index)
        unmatched.update(open_at)
        return "".join(char for index, char in enumerate(cleaned) if index not in unmatched)
