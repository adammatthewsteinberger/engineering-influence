# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The checks and shaping every search provider shares: the query, the links, the error."""

from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.search_results_interface import SearchResultsInterface
from engineering_influence.models.search_hit import SearchHit


class SearchResults(SearchResultsInterface):
    """What a provider does the same way whichever service it asks."""

    @staticmethod
    def check_query(query: str, count: int, max_characters: int, max_count: int) -> str:
        """The query with its whitespace collapsed, checked for length and for the count the caller asked for; raise SEARCH_QUERY_INVALID otherwise."""
        text = " ".join(query.split())
        if not text or len(text) > max_characters:
            raise SearchResults.error(
                "SEARCH_QUERY_INVALID", f"a search query is 1 to {max_characters} characters"
            )
        if not 1 <= count <= max_count:
            raise SearchResults.error("SEARCH_QUERY_INVALID", f"count is 1 to {max_count}")
        return text

    @staticmethod
    def hits(entries: list[Any], count: int) -> tuple[SearchHit, ...]:
        """The first count distinct hits, by URL, of the entries the search returned."""
        seen: dict[str, SearchHit] = {}
        for entry in entries:
            hit = SearchResults.hit(entry)
            if hit is not None and hit.url not in seen:
                seen[hit.url] = hit
        return tuple(seen.values())[:count]

    @staticmethod
    def hit(entry: Any) -> SearchHit | None:
        """One search entry as a hit, or None when it has no usable URL."""
        if not isinstance(entry, dict):
            return None
        url, title = entry.get("url"), entry.get("title")
        if not isinstance(url, str):
            return None
        try:
            return SearchHit(url, title if isinstance(title, str) else "")
        except ValueError:
            return None

    @staticmethod
    def error(code: str, message: str) -> ApplicationError:
        """The error for a search that failed upstream, which stops the stage as a bad upstream reply."""
        return ApplicationError(code=code, message=message, http_status=502)
