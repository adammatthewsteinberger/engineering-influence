# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""HttpBundleFetcher: one request to the address that was checked, no redirects, bounded in size and time."""

import gzip
import itertools
from collections.abc import Callable
from urllib.parse import urlsplit

import httpx
import pytest
from local_server import LocalServer, Reply

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.plugins.http_bundle_fetcher import HttpBundleFetcher
from engineering_influence.interfaces.bundle_fetcher_interface import BundleFetcherInterface
from engineering_influence.interfaces.outbound_url_pinner_interface import (
    OutboundUrlPinnerInterface,
)
from engineering_influence.models.pin_decision import PinDecision
from engineering_influence.models.pinned_target import PinnedTarget


class Pinner(OutboundUrlPinnerInterface):
    """Pins every address to itself, unless told to refuse a path; remembers each ask."""

    def __init__(self, refuse: str = "") -> None:
        self.refuse = refuse
        self.checked: list[str] = []

    def pin(self, url: str) -> PinDecision:
        self.checked.append(url)
        parts = urlsplit(url)
        if self.refuse and parts.path == self.refuse:
            return PinDecision.refused("blocked_here")
        return PinDecision.pinned(PinnedTarget(url, parts.netloc))


class ToServer(OutboundUrlPinnerInterface):
    """Pins a name to the address of a local server, as the real pinner pins it to what it resolved."""

    def __init__(self, base: str) -> None:
        self.base = base

    def pin(self, url: str) -> PinDecision:
        parts = urlsplit(url)
        return PinDecision.pinned(PinnedTarget(f"{self.base}{parts.path}", parts.netloc))


def fetcher(
    pinner: OutboundUrlPinnerInterface | None = None,
    seconds: float = 30.0,
    clock: Callable[[], float] | None = None,
) -> HttpBundleFetcher:
    options = {"clock": clock} if clock else {}
    return HttpBundleFetcher(
        httpx.Client(timeout=5.0), pinner or Pinner(), request_seconds=seconds, **options
    )


def reply(body: bytes = b"data", status: int = 200, **headers: str) -> Reply:
    return status, headers, body


def error_of(call: Callable[[], object]) -> ApplicationError:
    with pytest.raises(ApplicationError) as caught:
        call()
    return caught.value


def test_it_is_a_bundle_fetcher() -> None:
    assert isinstance(fetcher(), BundleFetcherInterface)


def test_it_returns_the_bytes_and_says_nothing_about_them() -> None:
    with LocalServer(
        lambda r: reply(b"\x00\xffnot even text", **{"content-type": "image/png"})
    ) as server:
        assert fetcher().fetch(f"{server.url}/x", 1000) == b"\x00\xffnot even text"


def test_it_sends_one_plain_request_with_no_identity_and_asks_for_no_compression() -> None:
    with LocalServer(lambda r: reply()) as server:
        fetcher().fetch(f"{server.url}/p", 1000)
    (request,) = server.seen
    assert request.method == "GET" and request.path() == "/p"
    assert request.headers["user-agent"] == "engineering-influence-bundle-fetcher"
    assert request.headers["accept-encoding"] == "identity"
    assert request.headers["connection"] == "close"
    assert not {"cookie", "authorization", "referer"} & request.headers.keys()


def test_it_connects_to_the_address_that_was_checked_with_the_name_in_the_host_header() -> None:
    with LocalServer(lambda r: reply(b"hello")) as server:
        found = fetcher(ToServer(server.url)).fetch("https://plugins.example.com/list.toml", 1000)
    assert found == b"hello"
    (request,) = server.seen
    assert request.path() == "/list.toml" and request.headers["host"] == "plugins.example.com"


def test_the_pinner_is_asked_before_the_request_and_a_refusal_sends_nothing() -> None:
    pinner = Pinner(refuse="/private")
    with LocalServer(lambda r: reply()) as server:
        error = error_of(lambda: fetcher(pinner).fetch(f"{server.url}/private?token=SECRET", 1000))
    assert server.seen == []
    assert (error.code, error.http_status) == ("BUNDLE_URL_REFUSED", 422)
    assert error.message == "127.0.0.1 refused: blocked_here" and "SECRET" not in error.message
    assert pinner.checked == [f"{server.url}/private?token=SECRET"]


def test_a_redirect_is_never_followed() -> None:
    with LocalServer(lambda r: reply(b"", 302, location="http://127.0.0.1:1/inside")) as server:
        error = error_of(lambda: fetcher().fetch(f"{server.url}/x", 1000))
    assert (error.code, error.http_status) == ("BUNDLE_REDIRECT_REFUSED", 502)
    assert "redirect, which is not followed" in error.message and len(server.seen) == 1


def test_a_missing_file_is_not_found_and_a_refusal_is_an_error() -> None:
    for status in (404, 410):
        with LocalServer(lambda r, status=status: reply(b"", status)) as server:  # type: ignore[misc]
            error = error_of(lambda: fetcher().fetch(f"{server.url}/x", 1000))
        assert error.code == "BUNDLE_NOT_FOUND" and f"answered {status}" in error.message
    for status in (400, 401, 403, 418):
        with LocalServer(lambda r, status=status: reply(b"", status)) as server:  # type: ignore[misc]
            error = error_of(lambda: fetcher().fetch(f"{server.url}/x", 1000))
        assert error.code == "BUNDLE_HTTP_ERROR" and f"answered {status}" in error.message


def test_a_timeout_a_rate_limit_or_a_server_error_is_worth_trying_again() -> None:
    for status in (408, 425, 429, 500, 503):
        server = LocalServer(lambda r, status=status: reply(b"", status))  # type: ignore[misc]
        with server, pytest.raises(TransientStageError, match=f"answered {status}"):
            fetcher().fetch(f"{server.url}/x", 1000)


def test_a_compressed_body_is_refused_and_an_identity_one_is_read() -> None:
    packed = gzip.compress(b"data")
    with LocalServer(lambda r: reply(packed, **{"content-encoding": "gzip"})) as server:
        error = error_of(lambda: fetcher().fetch(f"{server.url}/x", 1000))
    assert (
        error.code == "BUNDLE_REPLY_INVALID" and "only uncompressed files are read" in error.message
    )
    for encoding in ("identity", "", "IDENTITY"):
        with LocalServer(lambda r, e=encoding: reply(b"data", **{"content-encoding": e})) as server:  # type: ignore[misc]
            assert fetcher().fetch(f"{server.url}/x", 1000) == b"data"


def test_a_declared_length_over_the_cap_is_refused_before_the_body_is_read() -> None:
    with LocalServer(lambda r: reply(b"x" * 20)) as server:
        error = error_of(lambda: fetcher().fetch(f"{server.url}/x", 10))
    assert (error.code, error.http_status) == ("BUNDLE_TOO_LARGE", 502)
    assert "more than 10 bytes" in error.message


def test_a_body_with_no_declared_length_is_cut_off_at_the_cap() -> None:
    with LocalServer(lambda r: reply(b"x" * 11, **{"x-omit-length": "1"})) as server:
        assert (
            "more than 10 bytes" in error_of(lambda: fetcher().fetch(f"{server.url}/x", 10)).message
        )
    with LocalServer(lambda r: reply(b"x" * 10, **{"x-omit-length": "1"})) as server:
        assert fetcher().fetch(f"{server.url}/x", 10) == b"x" * 10


def test_a_body_exactly_at_the_cap_is_read_and_one_more_byte_is_not() -> None:
    with LocalServer(lambda r: reply(b"x" * 10)) as server:
        assert fetcher().fetch(f"{server.url}/x", 10) == b"x" * 10
    with LocalServer(lambda r: reply(b"x" * 11)) as server:
        assert error_of(lambda: fetcher().fetch(f"{server.url}/x", 10)).code == "BUNDLE_TOO_LARGE"


def test_a_download_that_takes_too_long_is_cut_off() -> None:
    clock = itertools.chain([0.0], itertools.repeat(100.0))
    server = LocalServer(lambda r: reply(b"data"))
    with server, pytest.raises(TransientStageError, match="did not finish sending in 30 seconds"):
        fetcher(clock=lambda: next(clock)).fetch(f"{server.url}/x", 1000)


def test_a_download_within_its_time_is_read() -> None:
    clock = itertools.chain([0.0], itertools.repeat(29.0))
    with LocalServer(lambda r: reply(b"data")) as server:
        assert fetcher(clock=lambda: next(clock)).fetch(f"{server.url}/x", 1000) == b"data"


def test_a_host_that_cannot_be_reached_is_worth_trying_again_and_is_named_without_the_address() -> (
    None
):
    with pytest.raises(
        TransientStageError, match=r"127\.0\.0\.1 could not be reached: ConnectError"
    ) as caught:
        fetcher().fetch("http://127.0.0.1:1/secret/path?token=SECRET", 1000)
    assert "SECRET" not in str(caught.value)


def test_a_cookie_a_server_sets_is_never_sent_back() -> None:
    with LocalServer(lambda r: reply(b"data", **{"set-cookie": "session=abc"})) as server:
        fetch = fetcher()
        fetch.fetch(f"{server.url}/one", 1000)
        fetch.fetch(f"{server.url}/two", 1000)
    assert all("cookie" not in request.headers for request in server.seen)


def test_the_limits_must_leave_room_to_work() -> None:
    with pytest.raises(ValueError, match="gets some time"):
        fetcher(seconds=0)
    with pytest.raises(ValueError, match="at least one byte"):
        fetcher().fetch("https://plugins.example.com/x", 0)
