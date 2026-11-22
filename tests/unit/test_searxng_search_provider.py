# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""SearxngSearchProvider: the request it sends, what it keeps, and how each failure is sorted."""

import json
from collections.abc import Callable
from typing import Any

import httpx
import pytest
from local_server import LocalServer, Reply, Seen

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.research.searxng_search_provider import (
    SearxngSearchProvider,
)
from engineering_influence.interfaces.search_provider_interface import SearchProviderInterface
from engineering_influence.models.search_hit import SearchHit


def reply(body: Any, status: int = 200) -> Reply:
    return status, {"content-type": "application/json"}, json.dumps(body).encode()


def results(*entries: Any) -> Reply:
    return reply({"query": "bees", "results": list(entries)})


def provider(base_url: str) -> SearxngSearchProvider:
    return SearxngSearchProvider(httpx.Client(timeout=2.0), base_url)


def search(
    route: Callable[[Seen], Reply], query: str = "bees", count: int = 5
) -> tuple[SearchHit, ...]:
    with LocalServer(route) as server:
        return provider(server.url).search(query, count)


def refused(route: Callable[[Seen], Reply], code: str, query: str = "bees", count: int = 5) -> str:
    with pytest.raises(ApplicationError) as error:
        search(route, query, count)
    assert (error.value.code, error.value.http_status) == (code, 502)
    return error.value.message


def test_it_is_a_search_provider() -> None:
    assert isinstance(provider("http://x.test"), SearchProviderInterface)


def test_it_sends_one_get_asking_for_json_and_no_key() -> None:
    with LocalServer(lambda r: results()) as server:
        provider(server.url).search("  honey   bees  ", 7)
    (request,) = server.seen
    assert request.method == "GET"
    assert request.target == "/search?q=honey+bees&format=json"
    assert request.headers["accept"] == "application/json"
    assert "authorization" not in request.headers and "x-subscription-token" not in request.headers


@pytest.mark.parametrize("address", ["http://searx.test/", "  http://searx.test  "])
def test_a_trailing_slash_or_stray_space_on_the_address_makes_no_difference(address: str) -> None:
    sent: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json={"results": []})

    SearxngSearchProvider(httpx.Client(transport=httpx.MockTransport(answer)), address).search(
        "bees", 1
    )
    assert str(sent[0].url).startswith("http://searx.test/search?")


def test_an_instance_under_a_path_is_searched_under_that_path() -> None:
    sent: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json={"results": []})

    client = httpx.Client(transport=httpx.MockTransport(answer))
    SearxngSearchProvider(client, "https://example.test/searx/").search("bees", 1)
    assert sent[0].url.path == "/searx/search"


def test_it_keeps_the_link_and_title_and_not_the_snippet() -> None:
    hits = search(
        lambda r: results(
            {"url": "https://a.test/1", "title": "A", "content": "an engine snippet"},
            {"url": "https://b.test/2", "title": "B", "engines": ["x"], "score": 2.0},
        )
    )
    assert hits == (SearchHit("https://a.test/1", "A"), SearchHit("https://b.test/2", "B"))


def test_it_returns_no_more_than_asked_for_and_never_the_same_link_twice() -> None:
    entries = [{"url": f"https://a.test/{n % 4}", "title": f"T{n}"} for n in range(10)]
    hits = search(lambda r: results(*entries), count=3)
    assert [hit.url for hit in hits] == ["https://a.test/0", "https://a.test/1", "https://a.test/2"]
    assert [hit.title for hit in hits] == ["T0", "T1", "T2"]


def test_an_entry_that_is_not_a_usable_link_is_skipped_not_fatal() -> None:
    hits = search(
        lambda r: results(
            "not a dict",
            {"title": "no url"},
            {"url": 5, "title": "numeric url"},
            {"url": "ftp://a.test/x", "title": "wrong scheme"},
            {"url": "https://u:p@a.test/x", "title": "credentials"},
            {"url": "https://ok.test/", "title": 7},
        )
    )
    assert hits == (SearchHit("https://ok.test/", ""),)


@pytest.mark.parametrize("body", [{}, {"results": []}, {"query": "bees"}])
def test_a_reply_with_no_results_is_no_hits(body: Any) -> None:
    assert search(lambda r: reply(body)) == ()


@pytest.mark.parametrize(
    "body", [[], "text", 5, {"results": "x"}, {"results": {"a": 1}}, {"results": None}]
)
def test_a_reply_in_an_unknown_shape_is_refused(body: Any) -> None:
    refused(lambda r: reply(body), "SEARCH_UNEXPECTED_REPLY")


def test_a_reply_that_is_not_json_is_refused() -> None:
    refused(lambda r: (200, {}, b"<html>"), "SEARCH_UNEXPECTED_REPLY")


@pytest.mark.parametrize("query", ["", "   ", "\n\t"])
def test_an_empty_query_is_refused_and_nothing_is_sent(query: str) -> None:
    with LocalServer(lambda r: results()) as server, pytest.raises(ApplicationError) as error:
        provider(server.url).search(query, 5)
    assert error.value.code == "SEARCH_QUERY_INVALID"
    assert server.seen == []


def test_a_query_is_limited_to_400_characters_after_whitespace_is_tidied() -> None:
    with LocalServer(lambda r: results()) as server:
        provider(server.url).search("a" * 400, 5)
        provider(server.url).search("  " + "a " * 200 + "  ", 5)
        with pytest.raises(ApplicationError, match="1 to 400"):
            provider(server.url).search("a" * 401, 5)
    assert len(server.seen) == 2


@pytest.mark.parametrize("count", [1, 20])
def test_the_ends_of_the_count_range_are_allowed(count: int) -> None:
    search(lambda r: results(), count=count)


@pytest.mark.parametrize("count", [0, -1, 21])
def test_a_count_outside_the_range_is_refused_and_nothing_is_sent(count: int) -> None:
    with LocalServer(lambda r: results()) as server, pytest.raises(ApplicationError) as error:
        provider(server.url).search("bees", count)
    assert (error.value.code, error.value.message) == ("SEARCH_QUERY_INVALID", "count is 1 to 20")
    assert server.seen == []


def test_a_403_says_to_enable_the_json_format() -> None:
    message = refused(lambda r: reply({"error": "no"}, 403), "SEARCH_REJECTED")
    assert "403" in message and "search.formats" in message and "settings.yml" in message


@pytest.mark.parametrize("status", [429, 500, 502, 503])
def test_a_rate_limit_or_server_failure_is_transient(status: int) -> None:
    with pytest.raises(TransientStageError, match=f"answered {status}"):
        search(lambda r: reply({"error": "later"}, status))


@pytest.mark.parametrize("status", [400, 401, 404, 422])
def test_any_other_rejection_is_an_error_with_its_status(status: int) -> None:
    message = refused(lambda r: reply({"error": "bad"}, status), "SEARCH_REJECTED")
    assert message == f"SearXNG rejected the request ({status})"


@pytest.mark.parametrize("status", [204, 301, 304])
def test_a_success_that_is_not_a_200_or_a_redirect_is_not_followed_or_trusted(
    status: int,
) -> None:
    refused(lambda r: (status, {"location": "http://elsewhere.test/"}, b""), "SEARCH_REJECTED")


def test_a_server_that_is_not_there_is_transient() -> None:
    with LocalServer(lambda r: results()) as server:
        url = server.url
    with pytest.raises(TransientStageError, match="could not be reached: ConnectError"):
        provider(url).search("bees", 5)


@pytest.mark.parametrize(
    "address",
    [
        "",
        "   ",
        "searx.test",
        "ftp://searx.test",
        "http://",
        "http://user:pass@searx.test",
        "http://searx.test/?q=1",
        "http://searx.test/#frag",
    ],
)
def test_an_address_that_is_not_a_plain_http_or_https_instance_is_refused(address: str) -> None:
    with pytest.raises(ValueError, match="SearXNG address"):
        SearxngSearchProvider(httpx.Client(), address)


@pytest.mark.parametrize("address", ["http://127.0.0.1:8888", "https://search.example/"])
def test_a_local_or_remote_instance_address_is_accepted(address: str) -> None:
    assert isinstance(SearxngSearchProvider(httpx.Client(), address), SearchProviderInterface)
