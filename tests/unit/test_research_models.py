# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""SearchHit, PageText and FetchedPage: what they refuse, and what they work out."""

import hashlib

import pytest

from engineering_influence.models.fetched_page import FetchedPage
from engineering_influence.models.page_text import PageText
from engineering_influence.models.search_hit import SearchHit
from engineering_influence.models.source_record import SourceRecord


@pytest.mark.parametrize("url", ["http://a.test/x", "https://a.test/x?q=1", "https://A.TEST"])
def test_a_search_hit_is_an_http_or_https_link_with_a_host(url: str) -> None:
    assert SearchHit(url, "A page").url == url


@pytest.mark.parametrize(
    "url",
    [
        "ftp://a.test/x",
        "file:///etc/passwd",
        "javascript:alert(1)",
        "//a.test/x",
        "a.test/x",
        "https://",
        "",
        "https://user:pass@a.test/x",
        "https://user@a.test/x",
        "https://:secret@a.test/x",
    ],
)
def test_a_search_hit_refuses_anything_else(url: str) -> None:
    with pytest.raises(ValueError, match="search hit"):
        SearchHit(url, "A page")


def test_a_search_hit_may_have_no_title_and_names_its_host_in_lower_case() -> None:
    hit = SearchHit("https://Example.TEST:8443/a/b", "")
    assert (hit.title, hit.host()) == ("", "example.test")


def test_a_page_text_is_empty_when_a_reader_would_see_nothing() -> None:
    assert PageText("Title", "").is_empty()
    assert PageText("Title", " \n\t ").is_empty()
    assert not PageText("", "words").is_empty()


@pytest.mark.parametrize(
    ("url", "text"),
    [("", "text"), ("  ", "text"), ("https://a.test", ""), ("https://a.test", "  \n")],
)
def test_a_fetched_page_needs_an_address_and_some_text(url: str, text: str) -> None:
    with pytest.raises(ValueError):
        FetchedPage(url, "Title", text)


def test_the_content_hash_is_the_sha256_of_the_utf8_text() -> None:
    page = FetchedPage("https://a.test", "T", "Caf\u00e9 \u2014 bees")
    assert page.content_hash() == hashlib.sha256("Caf\u00e9 \u2014 bees".encode()).hexdigest()
    other = FetchedPage("https://a.test", "T", "Cafe \u2014 bees")
    assert other.content_hash() != page.content_hash()


def test_the_hash_does_not_depend_on_the_title_or_the_address() -> None:
    first = FetchedPage("https://a.test/1", "One", "same text")
    second = FetchedPage("https://b.test/2", "Two", "same text")
    assert first.content_hash() == second.content_hash()


def test_a_fetched_page_becomes_an_unverified_source_record() -> None:
    page = FetchedPage("https://a.test/x", "  A Title  ", "the text")
    assert page.to_source() == SourceRecord(
        "https://a.test/x", "A Title", page.content_hash(), verified=False
    )


def test_a_page_with_no_title_is_titled_by_its_address() -> None:
    page = FetchedPage("https://a.test/x", "   ", "the text")
    assert page.to_source().title == "https://a.test/x"
