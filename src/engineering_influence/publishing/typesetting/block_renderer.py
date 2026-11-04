"""Block-level Markdown tokens to LaTeX for the fine-book class."""

from typing import ClassVar

from markdown_it.token import Token

from engineering_influence.publishing.typesetting.inline_renderer import InlineRenderer
from engineering_influence.publishing.typesetting.latex_table import LatexTable
from engineering_influence.publishing.typesetting.manuscript_error import ManuscriptError
from engineering_influence.publishing.typesetting.opening_formatter import OpeningFormatter


class BlockRenderer:
    """Renders headings, paragraphs, lists, quotes, tables, and code."""

    HEADINGS: ClassVar[dict[int, str]] = {2: r"\booksection", 3: r"\booksubsection"}
    # Tokens that print nothing: list item ends, table sections, section rules, raw HTML.
    IGNORED: ClassVar[frozenset[str]] = frozenset(
        {
            "list_item_close",
            "thead_open",
            "thead_close",
            "tbody_open",
            "tbody_close",
            "hr",
            "html_block",
        }
    )

    def __init__(self, style: str = "prose", openings: OpeningFormatter | None = None) -> None:
        self.style = style
        self.first_paragraph_pending = style == "prose"
        self._inline = InlineRenderer()
        self._openings = openings or OpeningFormatter()

    def render(self, tokens: list[Token]) -> str:
        """Render a token stream."""
        out: list[str] = []
        i = 0
        list_stack: list[str] = []
        quote_depth = 0
        table_rows: list[list[str]] = []
        row: list[str] = []
        while i < len(tokens):
            token = tokens[i]
            kind = token.type
            if kind == "heading_open":
                level = int(token.tag[1])
                text = self._inline.inline(tokens[i + 1].children or [])
                if level == 1:
                    raise ManuscriptError("a chapter may contain only one level-1 heading")
                command = self.HEADINGS.get(level, r"\booksubsubsection")
                out.append(f"\n{command}{{{text}}}\n")
                self.first_paragraph_pending = False
                i += 3
                continue
            if kind == "paragraph_open":
                text = self._inline.inline(tokens[i + 1].children or [])
                if list_stack:
                    out.append(text + "\n")
                elif self.style == "references":
                    out.append("\n\\refentry{" + text + "}\n")
                else:
                    if self.first_paragraph_pending and quote_depth == 0:
                        text = self._openings.format(text)
                        self.first_paragraph_pending = False
                    out.append("\n" + text + "\n")
                i += 3
                continue
            if kind == "bullet_list_open":
                list_stack.append("itemize")
                out.append("\n\\begin{itemize}\n")
            elif kind == "ordered_list_open":
                list_stack.append("enumerate")
                start = token.attrGet("start")
                option = f"[start={start}]" if start and str(start) != "1" else ""
                out.append(f"\n\\begin{{enumerate}}{option}\n")
            elif kind in ("bullet_list_close", "ordered_list_close"):
                out.append(f"\\end{{{list_stack.pop()}}}\n")
            elif kind == "list_item_open":
                out.append(r"\item ")
            elif kind == "blockquote_open":
                quote_depth += 1
                out.append("\n\\begin{quote}\n")
            elif kind == "blockquote_close":
                quote_depth -= 1
                out.append("\\end{quote}\n")
            elif kind == "table_open":
                table_rows = []
            elif kind == "tr_open":
                row = []
            elif kind in ("th_open", "td_open"):
                row.append(self._inline.inline(tokens[i + 1].children or []))
                i += 3
                continue
            elif kind == "tr_close":
                table_rows.append(row)
            elif kind == "table_close":
                out.append(LatexTable().render(table_rows))
            elif kind in ("fence", "code_block"):
                out.append("\n\\begin{verbatim}\n" + token.content + "\\end{verbatim}\n")
            elif kind not in self.IGNORED:
                raise ManuscriptError(f"unhandled block token {kind}")
            i += 1
        return "".join(out)
