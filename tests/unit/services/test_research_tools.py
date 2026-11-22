# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""WebSearchTool and FetchUrlTool: thin wrappers whose results the runner marks as untrusted."""

import hashlib
from typing import Any

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.search_provider_interface import SearchProviderInterface
from engineering_influence.interfaces.source_fetcher_interface import SourceFetcherInterface
from engineering_influence.interfaces.tool_interface import ToolInterface
from engineering_influence.models.fetched_page import FetchedPage
from engineering_influence.models.search_hit import SearchHit
from engineering_influence.services.fetch_url_tool import FetchUrlTool
from engineering_influence.services.web_search_tool import WebSearchTool


class Search(SearchProviderInterface):
    def __init__(self, *hits: SearchHit, fail: ApplicationError | None = None) -> None:
        self.hits, self.fail = hits, fail
        self.asked: list[tuple[str, int]] = []

    def search(self, query: str, count: int) -> tuple[SearchHit, ...]:
        self.asked.append((query, count))
        if self.fail:
            raise self.fail
        return self.hits


class Fetcher(SourceFetcherInterface):
    def __init__(self, page: FetchedPage | None = None, fail: ApplicationError | None = None):
        self.page, self.fail = page, fail
        self.asked: list[str] = []

    def fetch(self, url: str) -> FetchedPage:
        self.asked.append(url)
        if self.fail:
            raise self.fail
        assert self.page is not None
        return self.page


# --------------------------------------------------------------------------- web_search
def test_the_search_tool_is_a_tool_with_a_strict_schema() -> None:
    tool = WebSearchTool(Search())
    assert isinstance(tool, ToolInterface)
    definition = tool.definition()
    assert definition.name == "web_search"
    assert "fetch_url" in definition.description and "no page text" in definition.description
    assert definition.check({"query": "bees"}) == ""
    assert definition.check({"query": "bees", "count": 3}) == ""
    assert definition.check({}) == "missing the required argument 'query'"
    assert definition.check({"query": "bees", "count": "3"}) == (
        "argument 'count' must be of type integer"
    )
    assert definition.check({"query": "bees", "region": "us"}) == "unknown argument 'region'"


def test_hits_come_back_numbered_with_title_then_link() -> None:
    search = Search(
        SearchHit("https://a.test/1", "First  page\n title"),
        SearchHit("https://b.test/2", "Second"),
    )
    text = WebSearchTool(search).invoke({"query": "bees"})
    assert text == "1. First page title\n   https://a.test/1\n2. Second\n   https://b.test/2"


def test_a_hit_with_no_title_is_listed_by_its_link() -> None:
    text = WebSearchTool(Search(SearchHit("https://a.test/1", "  "))).invoke({"query": "x"})
    assert text == "1. https://a.test/1\n   https://a.test/1"


def test_no_hits_is_said_plainly() -> None:
    assert WebSearchTool(Search()).invoke({"query": "bees"}) == "No results."


@pytest.mark.parametrize(
    ("arguments", "count"), [({"query": "bees"}, 5), ({"query": "bees", "count": 9}, 9)]
)
def test_the_query_and_count_reach_the_provider_with_a_default_of_five(
    arguments: dict[str, Any], count: int
) -> None:
    search = Search()
    WebSearchTool(search).invoke(arguments)
    assert search.asked == [("bees", count)]


def test_a_provider_error_goes_up_for_the_runner_to_show_the_model() -> None:
    error = ApplicationError(code="SEARCH_REJECTED", message="no", http_status=502)
    with pytest.raises(ApplicationError) as raised:
        WebSearchTool(Search(fail=error)).invoke({"query": "bees"})
    assert raised.value is error


# --------------------------------------------------------------------------- fetch_url
def test_the_fetch_tool_is_a_tool_with_a_strict_schema() -> None:
    tool = FetchUrlTool(Fetcher())
    assert isinstance(tool, ToolInterface)
    definition = tool.definition()
    assert definition.name == "fetch_url"
    assert definition.check({"url": "https://a.test/"}) == ""
    assert definition.check({}) == "missing the required argument 'url'"
    assert definition.check({"url": "https://a.test/", "x": 1}) == "unknown argument 'x'"


def test_a_page_comes_back_under_its_address_title_hash_and_text() -> None:
    page = FetchedPage("https://a.test/final", "  The  Bees\n", "Colonies hold many bees.")
    fetcher = Fetcher(page)
    text = FetchUrlTool(fetcher).invoke({"url": "https://a.test/start"})
    digest = hashlib.sha256(b"Colonies hold many bees.").hexdigest()
    assert text == (
        "Source: https://a.test/final\nTitle: The Bees\n"
        f"SHA-256: {digest}\n\nColonies hold many bees."
    )
    assert fetcher.asked == ["https://a.test/start"]


def test_a_page_with_no_title_is_titled_by_its_address() -> None:
    page = FetchedPage("https://a.test/x", " ", "Some text.")
    assert "Title: https://a.test/x\n" in FetchUrlTool(Fetcher(page)).invoke({"url": "u"})


def test_a_page_that_cannot_be_used_is_the_fetchers_error() -> None:
    error = ApplicationError(code="SOURCE_NOT_FOUND", message="gone", http_status=502)
    with pytest.raises(ApplicationError) as raised:
        FetchUrlTool(Fetcher(fail=error)).invoke({"url": "https://a.test/"})
    assert raised.value is error
