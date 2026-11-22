# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""LazyBundleFetcher: built on first use, and a missing dependency becomes a message that names the extra."""

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.plugins.lazy_bundle_fetcher import LazyBundleFetcher
from engineering_influence.interfaces.bundle_fetcher_interface import BundleFetcherInterface


class Real(BundleFetcherInterface):
    def __init__(self) -> None:
        self.asked: list[tuple[str, int]] = []

    def fetch(self, url: str, max_bytes: int) -> bytes:
        self.asked.append((url, max_bytes))
        return b"data"


def test_it_is_a_bundle_fetcher() -> None:
    assert isinstance(LazyBundleFetcher(Real), BundleFetcherInterface)


def test_the_real_fetcher_is_built_once_on_the_first_download_and_gets_the_arguments() -> None:
    built: list[Real] = []

    def build() -> Real:
        built.append(Real())
        return built[0]

    lazy = LazyBundleFetcher(build)
    assert built == []
    assert lazy.fetch("https://x.example/a", 10) == b"data"
    assert lazy.fetch("https://x.example/b", 20) == b"data"
    assert len(built) == 1
    assert built[0].asked == [("https://x.example/a", 10), ("https://x.example/b", 20)]


def test_a_missing_dependency_is_a_message_that_names_the_extra_and_the_package() -> None:
    def build() -> Real:
        raise ImportError("no httpx", name="httpx")

    with pytest.raises(ApplicationError) as error:
        LazyBundleFetcher(build).fetch("https://x.example/a", 10)
    assert (error.value.code, error.value.http_status) == ("BUNDLE_NEEDS_EXTRA", 503)
    assert "pip install 'engineering-influence[runtime]'" in error.value.message
    assert "(missing httpx)" in error.value.message


def test_a_dependency_with_no_name_is_still_a_message_and_a_later_try_builds_again() -> None:
    attempts = []

    def build() -> Real:
        attempts.append(1)
        if len(attempts) == 1:
            raise ImportError("broken")
        return Real()

    lazy = LazyBundleFetcher(build)
    with pytest.raises(ApplicationError, match=r"\(missing a dependency\)"):
        lazy.fetch("https://x.example/a", 10)
    assert lazy.fetch("https://x.example/a", 10) == b"data" and len(attempts) == 2
