# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A search that tries its first provider and falls back to a second."""

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.capacity_exhausted_error import CapacityExhaustedError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.search_provider_interface import SearchProviderInterface
from engineering_influence.models.search_hit import SearchHit


class FallbackSearchProvider(SearchProviderInterface):
    """Asks the primary provider, and asks the backup when the primary cannot help.

    The backup is asked when the primary fails (it cannot be reached, it is rate-limited or out
    of capacity, it refuses, or it sends a reply nobody understands) and when it finds nothing,
    which for a metasearch engine usually means its upstream engines are throttling it. A query
    the primary calls invalid is not retried on the backup, since the same query would be refused
    there too. If the backup fails as well, its error is the one raised, with the primary's as its
    context. The backup is only reached, and its vendor only told the query, when it is needed.
    """

    INVALID_QUERY = "SEARCH_QUERY_INVALID"

    def __init__(self, primary: SearchProviderInterface, backup: SearchProviderInterface) -> None:
        self._primary = primary
        self._backup = backup

    def search(self, query: str, count: int) -> tuple[SearchHit, ...]:
        """The primary's links, or else the backup's."""
        try:
            hits = self._primary.search(query, count)
        except ApplicationError as error:
            if error.code == self.INVALID_QUERY:
                raise
            return self._backup.search(query, count)
        except (TransientStageError, CapacityExhaustedError):
            return self._backup.search(query, count)
        return hits or self._backup.search(query, count)
