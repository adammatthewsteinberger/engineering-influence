# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""HttpSourceFetcher: it goes only where the policy allows, at every hop, and reads only text."""

import gzip
from collections.abc import Callable
from urllib.parse import urlsplit

import httpx
import pytest
from local_server import LocalServer, Reply, Seen

from engineering_influence.contracts.security_verdict import SecurityVerdict
from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.research.html_text_extractor import HtmlTextExtractor
from engineering_influence.infrastructure.research.http_source_fetcher import HttpSourceFetcher
from engineering_influence.infrastructure.security.public_https_url_policy import (
    PublicHttpsUrlPolicy,
)
from engineering_influence.interfaces.outbound_url_policy_interface import (
    OutboundUrlPolicyInterface,
)
from engineering_influence.interfaces.source_fetcher_interface import SourceFetcherInterface

HTML = "text/html; charset=utf-8"


class Policy(OutboundUrlPolicyInterface):
    """Accepts everything except the paths and hosts it was told to refuse; remembers each ask."""

    def __init__(self, paths: tuple[str, ...] = (), hosts: tuple[str, ...] = ()) -> None:
        self.paths, self.hosts = paths, hosts
        self.checked: list[str] = []

    def check(self, url: str) -> SecurityVerdict:
        self.checked.append(url)
        parts = urlsplit(url)
        if parts.path in self.paths or parts.hostname in self.hosts:
            return SecurityVerdict.reject("blocked_here")
        return SecurityVerdict.accept()


def page(body: str | bytes, kind: str = HTML, status: int = 200, **headers: str) -> Reply:
    data = body.encode() if isinstance(body, str) else body
    return status, {"content-type": kind, **headers}, data


def fetcher(
    policy: OutboundUrlPolicyInterface | None = None, timeout: float = 2.0, **limits: int
) -> tuple[HttpSourceFetcher, Policy]:
    checked = policy if isinstance(policy, Policy) else Policy()
    return (
        HttpSourceFetcher(
            httpx.Client(timeout=timeout), policy or checked, HtmlTextExtractor(), **limits
        ),
        checked,
    )


def refused(call: Callable[[], object], code: str) -> str:
    with pytest.raises(ApplicationError) as error:
        call()
    assert (error.value.code, error.value.http_status) == (code, 422)
    return error.value.message


def test_it_is_a_source_fetcher() -> None:
    assert isinstance(fetcher()[0], SourceFetcherInterface)


def test_it_reads_an_html_page_as_its_visible_text_and_title() -> None:
    with LocalServer(lambda r: page("<title>Bees</title><p>Bees pollinate.</p>")) as server:
        found = fetcher()[0].fetch(f"{server.url}/bees")
    assert (found.url, found.title, found.text) == (
        f"{server.url}/bees",
        "Bees",
        "Bees pollinate.",
    )


def test_it_sends_one_plain_request_with_no_identity() -> None:
    with LocalServer(lambda r: page("<p>x</p>")) as server:
        fetcher()[0].fetch(f"{server.url}/p")
    (request,) = server.seen
    assert request.method == "GET"
    assert request.headers["user-agent"] == "engineering-influence-source-fetcher"
    assert request.headers["accept"] == "text/html,text/plain"
    assert not {"cookie", "authorization", "referer"} & request.headers.keys()


def test_it_reads_plain_text() -> None:
    with LocalServer(lambda r: page("  some \n\n\n\n text ", "text/plain")) as server:
        found = fetcher()[0].fetch(server.url)
    assert (found.title, found.text) == ("", "some\n\ntext")


def test_a_content_type_in_any_case_and_with_parameters_is_accepted() -> None:
    with LocalServer(lambda r: page("<p>x</p>", "TEXT/HTML ; Charset=UTF-8")) as server:
        assert fetcher()[0].fetch(server.url).text == "x"
    with LocalServer(lambda r: page("<p>x</p>", "application/xhtml+xml")) as server:
        assert fetcher()[0].fetch(server.url).text == "x"


def test_the_charset_the_server_names_is_used() -> None:
    body = "<p>caf\u00e9</p>".encode("latin-1")
    with LocalServer(lambda r: page(body, "text/html; charset=iso-8859-1")) as server:
        assert fetcher()[0].fetch(server.url).text == "caf\u00e9"


def test_a_charset_nobody_knows_falls_back_to_utf8_instead_of_failing() -> None:
    with LocalServer(lambda r: page("<p>caf\u00e9</p>", "text/html; charset=x-nonsense")) as server:
        assert fetcher()[0].fetch(server.url).text == "caf\u00e9"


def test_a_compressed_page_is_decoded() -> None:
    body = gzip.compress(b"<p>zipped words</p>")
    with LocalServer(lambda r: page(body, HTML, **{"content-encoding": "gzip"})) as server:
        assert fetcher()[0].fetch(server.url).text == "zipped words"


def test_the_policy_is_asked_before_the_request_and_a_refusal_sends_nothing() -> None:
    with LocalServer(lambda r: page("<p>x</p>")) as server:
        fetch, policy = fetcher(Policy(paths=("/private",)))
        message = refused(
            lambda: fetch.fetch(f"{server.url}/private?token=SECRET"), "SOURCE_URL_REFUSED"
        )
    assert server.seen == []
    assert message == "127.0.0.1 refused: blocked_here"
    assert "SECRET" not in message
    assert policy.checked == [f"{server.url}/private?token=SECRET"]


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "ftp://a.test/x", "javascript:alert(1)", "/relative"]
)
def test_a_scheme_other_than_http_is_refused_before_the_policy_or_the_client(url: str) -> None:
    fetch, policy = fetcher()
    assert (
        refused(lambda: fetch.fetch(url), "SOURCE_URL_REFUSED")
        == "a source address must be http or https"
    )
    assert policy.checked == []


def test_a_redirect_is_followed_and_the_final_address_is_kept() -> None:
    def route(request: Seen) -> Reply:
        if request.path() == "/a":
            return 302, {"location": "/b"}, b""
        return page("<p>arrived</p>")

    with LocalServer(route) as server:
        fetch, policy = fetcher()
        found = fetch.fetch(f"{server.url}/a")
    assert (found.url, found.text) == (f"{server.url}/b", "arrived")
    assert policy.checked == [f"{server.url}/a", f"{server.url}/b"]


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_each_redirect_status_is_followed(status: int) -> None:
    def route(request: Seen) -> Reply:
        return (status, {"location": "/b"}, b"") if request.path() == "/a" else page("<p>ok</p>")

    with LocalServer(route) as server:
        assert fetcher()[0].fetch(f"{server.url}/a").url.endswith("/b")


def test_a_redirect_to_a_refused_place_is_stopped_before_anything_is_sent_there() -> None:
    def route(request: Seen) -> Reply:
        return 302, {"location": "/forbidden"}, b""

    with LocalServer(route) as server:
        fetch, _ = fetcher(Policy(paths=("/forbidden",)))
        refused(lambda: fetch.fetch(f"{server.url}/a"), "SOURCE_URL_REFUSED")
    assert [r.path() for r in server.seen] == ["/a"]


def test_a_redirect_to_another_host_is_checked_against_that_host() -> None:
    with LocalServer(lambda r: (302, {"location": "//internal.test/secret"}, b"")) as server:
        fetch, policy = fetcher(Policy(hosts=("internal.test",)))
        message = refused(lambda: fetch.fetch(f"{server.url}/a"), "SOURCE_URL_REFUSED")
    assert message == "internal.test refused: blocked_here"
    assert policy.checked[-1] == "http://internal.test/secret"
    assert len(server.seen) == 1


def test_a_redirect_to_a_scheme_that_is_not_http_is_refused() -> None:
    with LocalServer(lambda r: (302, {"location": "ftp://a.test/x"}, b"")) as server:
        fetch, policy = fetcher()
        refused(lambda: fetch.fetch(server.url), "SOURCE_URL_REFUSED")
    assert policy.checked == [server.url]


def test_a_redirect_that_does_not_say_where_is_refused() -> None:
    with LocalServer(lambda r: (302, {}, b"")) as server:
        message = refused(lambda: fetcher()[0].fetch(server.url), "SOURCE_UNAVAILABLE")
    assert message == "127.0.0.1 redirected without saying where"


def test_a_redirect_loop_stops_after_the_allowed_number_of_hops() -> None:
    with LocalServer(lambda r: (302, {"location": "/loop"}, b"")) as server:
        message = refused(
            lambda: fetcher(max_redirects=3)[0].fetch(f"{server.url}/loop"),
            "SOURCE_TOO_MANY_REDIRECTS",
        )
    assert len(server.seen) == 4
    assert message == "127.0.0.1 redirected more than 3 times"


def test_no_redirects_allowed_means_the_first_redirect_is_too_many() -> None:
    with LocalServer(lambda r: (302, {"location": "/b"}, b"")) as server:
        refused(lambda: fetcher(max_redirects=0)[0].fetch(server.url), "SOURCE_TOO_MANY_REDIRECTS")
    assert len(server.seen) == 1


def test_a_page_exactly_at_the_size_limit_is_read_and_one_byte_over_is_not() -> None:
    with LocalServer(lambda r: page("a" * 1000, "text/plain")) as server:
        assert len(fetcher(max_bytes=1000)[0].fetch(server.url).text) == 1000
    with LocalServer(lambda r: page("a" * 1001, "text/plain")) as server:
        message = refused(lambda: fetcher(max_bytes=1000)[0].fetch(server.url), "SOURCE_TOO_LARGE")
    assert message == "127.0.0.1 sent more than 1000 bytes"


def test_a_small_download_that_expands_past_the_limit_is_stopped() -> None:
    bomb = gzip.compress(b"a" * 5_000_000)
    assert len(bomb) < 20_000
    with LocalServer(lambda r: page(bomb, "text/plain", **{"content-encoding": "gzip"})) as server:
        refused(lambda: fetcher(max_bytes=100_000)[0].fetch(server.url), "SOURCE_TOO_LARGE")


@pytest.mark.parametrize(
    "kind", ["application/pdf", "image/png", "application/json", "text/css", ""]
)
def test_anything_that_is_not_html_or_plain_text_is_refused(kind: str) -> None:
    headers = {"content-type": kind} if kind else {}
    with LocalServer(lambda r: (200, headers, b"data")) as server:
        message = refused(lambda: fetcher()[0].fetch(server.url), "SOURCE_UNSUPPORTED_TYPE")
    assert message == f"127.0.0.1 sent {kind or 'no content type'}, not text"


@pytest.mark.parametrize("body", ["<script>x()</script>", "", "   \n "])
def test_a_page_with_no_readable_text_is_refused(body: str) -> None:
    with LocalServer(lambda r: page(body)) as server:
        refused(lambda: fetcher()[0].fetch(server.url), "SOURCE_EMPTY")


@pytest.mark.parametrize("status", [404, 410])
def test_a_page_that_is_gone_is_not_found(status: int) -> None:
    with LocalServer(lambda r: page("<p>gone</p>", status=status)) as server:
        message = refused(lambda: fetcher()[0].fetch(server.url), "SOURCE_NOT_FOUND")
    assert message == f"127.0.0.1 answered {status}"


@pytest.mark.parametrize("status", [400, 401, 403, 451])
def test_a_page_the_server_will_not_give_is_unavailable(status: int) -> None:
    with LocalServer(lambda r: page("<p>no</p>", status=status)) as server:
        refused(lambda: fetcher()[0].fetch(server.url), "SOURCE_UNAVAILABLE")


@pytest.mark.parametrize("status", [408, 425, 429, 500, 502, 503])
def test_a_failure_that_may_pass_is_transient(status: int) -> None:
    with (
        LocalServer(lambda r: page("<p>later</p>", status=status)) as server,
        pytest.raises(TransientStageError, match=f"127.0.0.1 answered {status}"),
    ):
        fetcher()[0].fetch(server.url)


def test_a_server_that_is_not_there_is_transient() -> None:
    with LocalServer(lambda r: page("x")) as server:
        url = server.url
    with pytest.raises(TransientStageError, match="could not be reached: ConnectError"):
        fetcher()[0].fetch(url)


def test_a_server_that_is_too_slow_is_transient() -> None:
    import time

    def slow(request: Seen) -> Reply:
        time.sleep(1.0)
        return page("<p>late</p>")

    with (
        LocalServer(slow) as server,
        pytest.raises(TransientStageError, match="could not be reached: ReadTimeout"),
    ):
        fetcher(timeout=0.2)[0].fetch(server.url)


def test_the_real_policy_refuses_plain_http_so_nothing_reaches_a_local_server() -> None:
    with LocalServer(lambda r: page("<p>x</p>")) as server:
        message = refused(
            lambda: fetcher(PublicHttpsUrlPolicy())[0].fetch(f"{server.url}/x"),
            "SOURCE_URL_REFUSED",
        )
    assert message == "127.0.0.1 refused: scheme_not_https"
    assert server.seen == []


def test_the_real_policy_refuses_a_name_that_resolves_to_a_private_address() -> None:
    def never(request: httpx.Request) -> httpx.Response:
        raise AssertionError("nothing may be sent to a refused address")

    policy = PublicHttpsUrlPolicy(resolver=lambda host: ["10.0.0.5"])
    fetch = HttpSourceFetcher(
        httpx.Client(transport=httpx.MockTransport(never)), policy, HtmlTextExtractor()
    )
    message = refused(
        lambda: fetch.fetch("https://looks-public.example.test/x"), "SOURCE_URL_REFUSED"
    )
    assert message == "looks-public.example.test refused: non_public_address"


@pytest.mark.parametrize(
    ("limits", "message"), [({"max_bytes": 0}, "limits"), ({"max_redirects": -1}, "limits")]
)
def test_the_limits_must_allow_a_fetch_at_all(limits: dict[str, int], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        fetcher(**limits)


@pytest.mark.parametrize("status", [204, 206, 300, 304])
def test_a_reply_that_is_neither_a_page_nor_a_redirect_is_unavailable(status: int) -> None:
    with LocalServer(lambda r: page("<p>x</p>", status=status)) as server:
        refused(lambda: fetcher()[0].fetch(server.url), "SOURCE_UNAVAILABLE")
