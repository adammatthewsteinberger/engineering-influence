# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Web search through the Brave Search API, over plain httpx."""

from typing import Any, ClassVar

import httpx

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.research.search_results import SearchResults
from engineering_influence.interfaces.search_provider_interface import SearchProviderInterface
from engineering_influence.models.search_hit import SearchHit


class BraveSearchProvider(SearchProviderInterface):
    """``GET /res/v1/web/search`` with the key in the ``X-Subscription-Token`` header.

    Written from Brave's documented request and response shape and tested against a local server
    that follows it; it has not been run against the live API. Only each result's link and title
    are kept. The adapter never retries: the exception type is the contract (as in ADR 0007), a
    refused key or exhausted plan is a CapacityExhaustedError, and a timeout, a 429 or a 5xx is a
    TransientStageError. A 429 can also mean the plan's quota is spent, which a retry will not
    fix; the run's attempt limit ends that. The query is sent to Brave, and the key never leaves
    the header or appears in an error.
    """

    MAX_QUERY_CHARACTERS = 400
    MAX_COUNT = 20
    CAPACITY: ClassVar[frozenset[int]] = frozenset({401, 402, 403})

    def __init__(
        self,
        client: httpx.Client,
        api_key: str,
        base_url: str = "https://api.search.brave.com",
    ) -> None:
        """Remember the HTTP client, the key and the service address."""
        if not api_key.strip():
            raise ValueError("a Brave Search provider needs an API key")
        self._client = client
        self._api_key = api_key.strip()
        self._base_url = base_url.rstrip("/")

    def search(self, query: str, count: int) -> tuple[SearchHit, ...]:
        """Up to ``count`` distinct links for the query, best first, or none."""
        text = SearchResults.check_query(query, count, self.MAX_QUERY_CHARACTERS, self.MAX_COUNT)
        try:
            response = self._client.get(
                f"{self._base_url}/res/v1/web/search",
                params={"q": text, "count": count},
                headers={"accept": "application/json", "x-subscription-token": self._api_key},
            )
        except httpx.TransportError as error:
            raise TransientStageError(
                f"Brave Search could not be reached: {type(error).__name__}"
            ) from error
        status = response.status_code
        if status in self.CAPACITY:
            raise CapacityExhaustedError(f"Brave Search refused the request ({status})")
        if status == 429 or status >= 500:
            raise TransientStageError(f"Brave Search answered {status}")
        if status != 200:
            raise self._error("SEARCH_REJECTED", f"Brave Search rejected the request ({status})")
        return self._hits(response, count)

    def _hits(self, response: httpx.Response, count: int) -> tuple[SearchHit, ...]:
        try:
            data: Any = response.json()
        except ValueError as error:
            raise self._unexpected() from error
        if not isinstance(data, dict):
            raise self._unexpected()
        results = (data.get("web") or {}).get("results") or []
        if not isinstance(results, list):
            raise self._unexpected()
        return SearchResults.hits(results, count)

    def _unexpected(self) -> ApplicationError:
        return self._error(
            "SEARCH_UNEXPECTED_REPLY",
            "Brave Search sent a reply in a shape this adapter does not know",
        )

    @staticmethod
    def _error(code: str, message: str) -> ApplicationError:
        return SearchResults.error(code, message)
