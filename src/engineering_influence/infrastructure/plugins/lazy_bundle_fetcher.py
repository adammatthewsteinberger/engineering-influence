# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Builds the HTTP fetcher only when something is first downloaded."""

from collections.abc import Callable

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.bundle_fetcher_interface import BundleFetcherInterface


class LazyBundleFetcher(BundleFetcherInterface):
    """So an install without the ``runtime`` extra still runs every command that reads a local file.

    Downloading needs ``httpx``, which the core install does not have. Building the fetcher is deferred
    to the first download, and a missing dependency becomes an error that names the extra to install
    instead of a traceback. Once built, the fetcher is kept.
    """

    def __init__(self, build: Callable[[], BundleFetcherInterface]) -> None:
        self._build = build
        self._fetcher: BundleFetcherInterface | None = None

    def fetch(self, url: str, max_bytes: int) -> bytes:
        """Build the real fetcher if this is the first download, then let it download."""
        if self._fetcher is None:
            try:
                self._fetcher = self._build()
            except ImportError as error:
                raise ApplicationError(
                    code="BUNDLE_NEEDS_EXTRA",
                    message="downloading over https needs the runtime extra: "
                    "pip install 'engineering-influence[runtime]' "
                    f"(missing {error.name or 'a dependency'})",
                    http_status=503,
                ) from error
        return self._fetcher.fetch(url, max_bytes)
