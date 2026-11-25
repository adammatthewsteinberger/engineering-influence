# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Block-level Markdown tokens to LaTeX for the fine-book class."""

import re
from typing import ClassVar

from markdown_it.token import Token

from engineering_influence.errors.typesetting.manuscript_error import ManuscriptError
from engineering_influence.services.typesetting.inline_renderer import InlineRenderer
from engineering_influence.services.typesetting.interfaces.block_renderer_interface import (
    BlockRendererInterface,
)
from engineering_influence.services.typesetting.latex_table import LatexTable
from engineering_influence.services.typesetting.opening_formatter import OpeningFormatter


class BlockRenderer(BlockRendererInterface):
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

    # LaTeX's verbatim environment ends at this text wherever it appears, and what follows on the
    # line is read as TeX, so a code block that contains it would run the rest of the line.
    VERBATIM_END = re.compile(r"\\end\s*\{\s*verbatim\*?\s*\}")

    def __init__(
        self,
        style: str = "prose",
        openings: OpeningFormatter | None = None,
        scene_breaks: bool = False,
    ) -> None:
        self.style = style
        self._scene_breaks = scene_breaks
        self.printed = False  # set once the chapter has printed anything, across its pieces
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
                if self.VERBATIM_END.search(token.content):
                    raise ManuscriptError(
                        "a code block contains \\end{verbatim}, which would end the code "
                        "environment early and let the rest of the line run as TeX"
                    )
                out.append("\n\\begin{verbatim}\n" + token.content + "\\end{verbatim}\n")
            elif kind == "hr" and self._is_scene_break(tokens, i, out, quote_depth, list_stack):
                out.append("\n\\scenebreak\n")
            elif kind not in self.IGNORED:
                raise ManuscriptError(f"unhandled block token {kind}")
            i += 1
        self.printed = self.printed or bool(out)
        return "".join(out)

    def _is_scene_break(
        self, tokens: list[Token], i: int, out: list[str], quote_depth: int, list_stack: list[str]
    ) -> bool:
        """A rule is a scene break only in fiction, between two passages, outside quotes and lists.

        A rule that opens or closes a passage, or that sits beside another rule, would print an
        ornament with nothing on one side, so it is left out. A callout or illustration counts as
        content on its side, so a rule right after one is kept.
        """
        return (
            self._scene_breaks
            and (bool(out) or self.printed)
            and quote_depth == 0
            and not list_stack
            and i + 1 < len(tokens)
            and tokens[i + 1].type != "hr"
        )
