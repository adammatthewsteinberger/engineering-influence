# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Web search through a SearXNG instance, over plain httpx."""

from typing import Any
from urllib.parse import urlsplit

import httpx

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.search_provider_interface import SearchProviderInterface
from engineering_influence.models.search_hit import SearchHit


class SearxngSearchProvider(SearchProviderInterface):
    """``GET /search?q=...&format=json`` against a SearXNG instance you run or trust.

    Written from SearXNG's documented request and response shape and tested against a local server
    that follows it; it has not been run against a live instance. The instance must list ``json``
    under ``search.formats`` in its ``settings.yml``, or it answers 403. SearXNG takes no result
    count, so the list is cut here. Only each result's link and title are kept. The adapter never
    retries: the exception type is the contract (as in ADR 0007). A timeout, a 429 (its rate
    limiter) or a 5xx is a TransientStageError, and any other refusal is an ApplicationError.
    There is no key and no plan, so nothing here is a capacity failure. The query goes to the
    instance, which sends it on to the search engines it is set to use.
    """

    MAX_QUERY_CHARACTERS = 400
    MAX_COUNT = 20

    def __init__(self, client: httpx.Client, base_url: str) -> None:
        parts = urlsplit(base_url.strip())
        if parts.scheme not in ("http", "https") or not parts.hostname:
            raise ValueError("a SearXNG address is an http or https URL with a host")
        if parts.username is not None or parts.query or parts.fragment:
            raise ValueError("a SearXNG address has no credentials, query or fragment")
        self._client = client
        self._base_url = base_url.strip().rstrip("/")

    def search(self, query: str, count: int) -> tuple[SearchHit, ...]:
        """Up to ``count`` distinct links for the query, best first, or none."""
        text = " ".join(query.split())
        if not text or len(text) > self.MAX_QUERY_CHARACTERS:
            raise self._error(
                "SEARCH_QUERY_INVALID",
                f"a search query is 1 to {self.MAX_QUERY_CHARACTERS} characters",
            )
        if not 1 <= count <= self.MAX_COUNT:
            raise self._error("SEARCH_QUERY_INVALID", f"count is 1 to {self.MAX_COUNT}")
        try:
            response = self._client.get(
                f"{self._base_url}/search",
                params={"q": text, "format": "json"},
                headers={"accept": "application/json"},
            )
        except httpx.TransportError as error:
            raise TransientStageError(
                f"SearXNG could not be reached: {type(error).__name__}"
            ) from error
        status = response.status_code
        if status == 429 or status >= 500:
            raise TransientStageError(f"SearXNG answered {status}")
        if status == 403:
            raise self._error(
                "SEARCH_REJECTED",
                "SearXNG refused the request (403); is json listed under search.formats "
                "in its settings.yml?",
            )
        if status != 200:
            raise self._error("SEARCH_REJECTED", f"SearXNG rejected the request ({status})")
        return self._hits(response, count)

    def _hits(self, response: httpx.Response, count: int) -> tuple[SearchHit, ...]:
        try:
            data: Any = response.json()
        except ValueError as error:
            raise self._unexpected() from error
        if not isinstance(data, dict) or not isinstance(data.get("results", []), list):
            raise self._unexpected()
        seen: dict[str, SearchHit] = {}
        for entry in data.get("results", []):
            hit = self._hit(entry)
            if hit is not None and hit.url not in seen:
                seen[hit.url] = hit
        return tuple(seen.values())[:count]

    @staticmethod
    def _hit(entry: Any) -> SearchHit | None:
        if not isinstance(entry, dict):
            return None
        url, title = entry.get("url"), entry.get("title")
        if not isinstance(url, str):
            return None
        try:
            return SearchHit(url, title if isinstance(title, str) else "")
        except ValueError:
            return None

    def _unexpected(self) -> ApplicationError:
        return self._error(
            "SEARCH_UNEXPECTED_REPLY",
            "SearXNG sent a reply in a shape this adapter does not know",
        )

    @staticmethod
    def _error(code: str, message: str) -> ApplicationError:
        return ApplicationError(code=code, message=message, http_status=502)
