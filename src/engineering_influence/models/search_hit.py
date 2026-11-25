# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One result of a web search: where it is, and what it calls itself."""

from dataclasses import dataclass
from urllib.parse import urlsplit

from engineering_influence.models.interfaces.search_hit_interface import SearchHitInterface


@dataclass(frozen=True, slots=True)
class SearchHit(SearchHitInterface):
    """A link and its title, and nothing else.

    Only the link is kept, never the vendor's snippet: the page is fetched directly and that text
    is what a source is pinned by, so the book's evidence does not depend on a search vendor's
    licence to store and reuse its text.
    """

    url: str
    title: str

    def __post_init__(self) -> None:
        parts = urlsplit(self.url)
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError("a search hit is an http or https link with a host")
        if parts.username is not None:
            raise ValueError("a search hit link carries no credentials")

    def host(self) -> str:
        """The host the link points at, in lower case."""
        return urlsplit(self.url).hostname or ""
