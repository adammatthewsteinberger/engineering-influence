# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Walks one HTML page and keeps only the text a reader would see."""

import re
from html.parser import HTMLParser

from engineering_influence.infrastructure.research.interfaces.html_collector_interface import (
    HtmlCollectorInterface,
)


class HtmlCollector(HTMLParser, HtmlCollectorInterface):
    """The parser for one page; feed it, close it, then ask what it collected.

    It tracks which elements are open, so everything inside a skipped or hidden element is
    dropped however deeply it is nested, and a stray or missing end tag cannot leave it skipping
    the rest of the page. One collector reads one page: it is not shared.
    """

    SKIPPED = frozenset(
        {"script", "style", "noscript", "template", "svg", "iframe", "object", "canvas"}
    )
    VOID = frozenset(
        {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source"}
        | {"track", "wbr"}
    )
    BLOCKS = frozenset(
        {"p", "div", "br", "li", "ul", "ol", "dl", "dt", "dd", "tr", "table", "section", "article"}
        | {"header", "footer", "main", "nav", "aside", "blockquote", "pre", "hr", "figure"}
        | {"figcaption", "form", "h1", "h2", "h3", "h4", "h5", "h6"}
    )
    HIDDEN_STYLE = re.compile(r"(?:display\s*:\s*none|visibility\s*:\s*hidden)", re.IGNORECASE)

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._title: list[str] = []
        self._open: list[tuple[str, bool]] = []
        self._hidden_depth = 0
        self._in_title = False

    def collected(self) -> tuple[str, str]:
        """The title and the visible text found so far, both before whitespace is cleaned up."""
        return "".join(self._title), "".join(self._parts)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """Note a block break, and open the element unless it has no content."""
        if tag in self.BLOCKS and not self._hidden_depth:
            self._parts.append("\n")
        if tag in self.VOID:
            return
        hidden = tag in self.SKIPPED or self._is_hidden(dict(attrs))
        self._open.append((tag, hidden))
        self._hidden_depth += hidden
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        """Close the nearest open element of that name, and everything opened inside it."""
        if tag in self.BLOCKS and not self._hidden_depth:
            self._parts.append("\n")
        if tag not in [name for name, _ in self._open]:
            return
        # The tag is open, so this stops at it; it cannot run the stack dry.
        while True:
            name, hidden = self._open.pop()
            self._hidden_depth -= hidden
            if name == "title":
                self._in_title = False
            if name == tag:
                return

    def handle_data(self, data: str) -> None:
        """Keep text that is not inside a hidden or skipped element."""
        if self._hidden_depth:
            return
        if self._in_title:
            self._title.append(data)
        else:
            self._parts.append(data)

    def _is_hidden(self, attrs: dict[str, str | None]) -> bool:
        if "hidden" in attrs:
            return True
        if (attrs.get("aria-hidden") or "").strip().lower() == "true":
            return True
        return bool(self.HIDDEN_STYLE.search(attrs.get("style") or ""))
