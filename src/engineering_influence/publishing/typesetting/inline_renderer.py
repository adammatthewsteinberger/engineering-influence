"""Inline Markdown tokens to LaTeX."""

import re

from markdown_it.token import Token

from engineering_influence.publishing.typesetting.latex_escaper import LatexEscaper
from engineering_influence.publishing.typesetting.manuscript_error import ManuscriptError


class InlineRenderer:
    """Renders emphasis, code, links, and bare URLs."""

    URL = re.compile(r"https?://[^\s<>\"\u201d\u2019)]+[^\s<>\"\u201d\u2019).,;:]")

    def __init__(self) -> None:
        self._escaper = LatexEscaper()
        self._href: str | None = None

    def text(self, s: str) -> str:
        """Escape text; bare URLs become breakable \\url{}."""
        # Smart quotes pair within one paragraph, so a quotation that runs across paragraphs
        # keeps straight marks. Curl those by position.
        s = re.sub(r'(^|(?<=[\s(\[{]))"', "\u201c", s).replace('"', "\u201d")
        out: list[str] = []
        pos = 0
        for match in self.URL.finditer(s):
            out.append(self._escaper.escape(s[pos : match.start()]))
            out.append(r"\url{" + self._url(match.group(0)) + "}")
            pos = match.end()
        out.append(self._escaper.escape(s[pos:]))
        return "".join(out)

    def inline(self, tokens: list[Token]) -> str:
        """Render a paragraph's inline tokens."""
        out: list[str] = []
        for token in tokens:
            kind = token.type
            if kind == "text":
                out.append(self.text(token.content))
            elif kind == "softbreak":
                out.append(" ")
            elif kind == "hardbreak":
                out.append("\\\\\n")
            elif kind == "em_open":
                out.append(r"\emph{")
            elif kind == "strong_open":
                out.append(r"\textbf{")
            elif kind in ("em_close", "strong_close", "s_close"):
                out.append("}")
            elif kind == "s_open":
                out.append(r"\sout{")
            elif kind == "code_inline":
                out.append(r"\texttt{" + self._escaper.escape(token.content) + "}")
            elif kind == "link_open":
                out.append("{")
                href = token.attrGet("href")
                self._href = str(href) if href is not None else None
            elif kind == "link_close":
                out.append("}")
                if self._href and self._href.startswith("http"):
                    out.append(r"\footnote{\url{" + self._url(self._href) + "}}")
            elif kind == "html_inline":
                continue
            elif kind == "image":
                raise ManuscriptError("images are not supported in the print pipeline")
            else:
                raise ManuscriptError(f"unhandled inline token {kind}")
        return "".join(out)

    def _url(self, url: str) -> str:
        return url.replace("%", r"\%").replace("#", r"\#")
