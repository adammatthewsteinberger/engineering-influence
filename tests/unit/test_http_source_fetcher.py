# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""HttpSourceFetcher: it goes only where the pinner allows, at every hop, and reads only text."""

import gzip
from collections.abc import Callable
from urllib.parse import urlsplit

import httpx
import pytest
from local_server import LocalServer, Reply, Seen

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.infrastructure.research.html_text_extractor import HtmlTextExtractor
from engineering_influence.infrastructure.research.http_source_fetcher import HttpSourceFetcher
from engineering_influence.infrastructure.security.public_https_url_pinner import (
    PublicHttpsUrlPinner,
)
from engineering_influence.infrastructure.security.public_https_url_policy import (
    PublicHttpsUrlPolicy,
)
from engineering_influence.interfaces.outbound_url_pinner_interface import (
    OutboundUrlPinnerInterface,
)
from engineering_influence.interfaces.source_fetcher_interface import SourceFetcherInterface
from engineering_influence.models.pin_decision import PinDecision
from engineering_influence.models.pinned_target import PinnedTarget

HTML = "text/html; charset=utf-8"


class Pinner(OutboundUrlPinnerInterface):
    """Pins every URL to itself except the paths and hosts it was told to refuse; remembers each ask."""

    def __init__(self, paths: tuple[str, ...] = (), hosts: tuple[str, ...] = ()) -> None:
        self.paths, self.hosts = paths, hosts
        self.checked: list[str] = []

    def pin(self, url: str) -> PinDecision:
        self.checked.append(url)
        parts = urlsplit(url)
        if parts.path in self.paths or parts.hostname in self.hosts:
            return PinDecision.refused("blocked_here")
        return PinDecision.pinned(PinnedTarget(url, parts.netloc))


def page(body: str | bytes, kind: str = HTML, status: int = 200, **headers: str) -> Reply:
    data = body.encode() if isinstance(body, str) else body
    return status, {"content-type": kind, **headers}, data


def fetcher(
    pinner: OutboundUrlPinnerInterface | None = None, timeout: float = 2.0, **limits: int
) -> tuple[HttpSourceFetcher, Pinner]:
    checked = pinner if isinstance(pinner, Pinner) else Pinner()
    return (
        HttpSourceFetcher(
            httpx.Client(timeout=timeout), pinner or checked, HtmlTextExtractor(), **limits
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


def test_the_pinner_is_asked_before_the_request_and_a_refusal_sends_nothing() -> None:
    with LocalServer(lambda r: page("<p>x</p>")) as server:
        fetch, pinner = fetcher(Pinner(paths=("/private",)))
        message = refused(
            lambda: fetch.fetch(f"{server.url}/private?token=SECRET"), "SOURCE_URL_REFUSED"
        )
    assert server.seen == []
    assert message == "127.0.0.1 refused: blocked_here"
    assert "SECRET" not in message
    assert pinner.checked == [f"{server.url}/private?token=SECRET"]


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "ftp://a.test/x", "javascript:alert(1)", "/relative"]
)
def test_a_scheme_other_than_http_is_refused_before_the_pinner_or_the_client(url: str) -> None:
    fetch, pinner = fetcher()
    assert (
        refused(lambda: fetch.fetch(url), "SOURCE_URL_REFUSED")
        == "a source address must be http or https"
    )
    assert pinner.checked == []


def test_a_redirect_is_followed_and_the_final_address_is_kept() -> None:
    def route(request: Seen) -> Reply:
        if request.path() == "/a":
            return 302, {"location": "/b"}, b""
        return page("<p>arrived</p>")

    with LocalServer(route) as server:
        fetch, pinner = fetcher()
        found = fetch.fetch(f"{server.url}/a")
    assert (found.url, found.text) == (f"{server.url}/b", "arrived")
    assert pinner.checked == [f"{server.url}/a", f"{server.url}/b"]


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
        fetch, _ = fetcher(Pinner(paths=("/forbidden",)))
        refused(lambda: fetch.fetch(f"{server.url}/a"), "SOURCE_URL_REFUSED")
    assert [r.path() for r in server.seen] == ["/a"]


def test_a_redirect_to_another_host_is_checked_against_that_host() -> None:
    with LocalServer(lambda r: (302, {"location": "//internal.test/secret"}, b"")) as server:
        fetch, pinner = fetcher(Pinner(hosts=("internal.test",)))
        message = refused(lambda: fetch.fetch(f"{server.url}/a"), "SOURCE_URL_REFUSED")
    assert message == "internal.test refused: blocked_here"
    assert pinner.checked[-1] == "http://internal.test/secret"
    assert len(server.seen) == 1


def test_a_redirect_to_a_scheme_that_is_not_http_is_refused() -> None:
    with LocalServer(lambda r: (302, {"location": "ftp://a.test/x"}, b"")) as server:
        fetch, pinner = fetcher()
        refused(lambda: fetch.fetch(server.url), "SOURCE_URL_REFUSED")
    assert pinner.checked == [server.url]


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
            lambda: fetcher(PublicHttpsUrlPinner(PublicHttpsUrlPolicy()))[0].fetch(
                f"{server.url}/x"
            ),
            "SOURCE_URL_REFUSED",
        )
    assert message == "127.0.0.1 refused: scheme_not_https"
    assert server.seen == []


def test_the_real_policy_refuses_a_name_that_resolves_to_a_private_address() -> None:
    def never(request: httpx.Request) -> httpx.Response:
        raise AssertionError("nothing may be sent to a refused address")

    pinner = PublicHttpsUrlPinner(PublicHttpsUrlPolicy(), lambda host: ["10.0.0.5"])
    fetch = HttpSourceFetcher(
        httpx.Client(transport=httpx.MockTransport(never)), pinner, HtmlTextExtractor()
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


def test_it_asks_for_an_uncompressed_body() -> None:
    with LocalServer(lambda r: page("<p>x</p>")) as server:
        fetcher()[0].fetch(server.url)
    assert server.seen[0].headers["accept-encoding"] == "identity"


@pytest.mark.parametrize(
    "encoding", ["gzip", "deflate", "br", "zstd", "GZIP", " gzip ", "gzip, br"]
)
def test_a_compressed_reply_is_refused_before_any_of_it_is_decoded(encoding: str) -> None:
    body = gzip.compress(b"<p>zipped</p>")
    with LocalServer(lambda r: page(body, HTML, **{"content-encoding": encoding})) as server:
        message = refused(lambda: fetcher()[0].fetch(server.url), "SOURCE_UNSUPPORTED_ENCODING")
    assert "only uncompressed pages are read" in message
    assert encoding.strip().lower() in message


def test_a_small_download_that_would_expand_enormously_is_never_expanded() -> None:
    bomb = gzip.compress(b"a" * 50_000_000)
    assert len(bomb) < 100_000
    with LocalServer(lambda r: page(bomb, "text/plain", **{"content-encoding": "gzip"})) as server:
        refused(
            lambda: fetcher(max_bytes=100_000)[0].fetch(server.url), "SOURCE_UNSUPPORTED_ENCODING"
        )


@pytest.mark.parametrize("encoding", ["identity", "Identity"])
def test_an_explicitly_uncompressed_reply_is_read(encoding: str) -> None:
    with LocalServer(
        lambda r: page("<p>plain</p>", HTML, **{"content-encoding": encoding})
    ) as server:
        assert fetcher()[0].fetch(server.url).text == "plain"


def test_a_declared_length_over_the_limit_is_refused_before_the_body_is_read() -> None:
    with LocalServer(lambda r: page("ok", "text/plain", **{"content-length": "1001"})) as server:
        message = refused(lambda: fetcher(max_bytes=1000)[0].fetch(server.url), "SOURCE_TOO_LARGE")
    assert message == "127.0.0.1 sent more than 1000 bytes"


def test_a_declared_length_at_the_limit_is_allowed() -> None:
    with LocalServer(
        lambda r: page("a" * 1000, "text/plain", **{"content-length": "1000"})
    ) as server:
        assert len(fetcher(max_bytes=1000)[0].fetch(server.url).text) == 1000


def test_a_body_with_no_declared_length_is_capped_as_it_streams() -> None:
    with LocalServer(lambda r: page("a" * 5000, "text/plain", **{"x-omit-length": "1"})) as server:
        refused(lambda: fetcher(max_bytes=1000)[0].fetch(server.url), "SOURCE_TOO_LARGE")
    assert "content-length" not in server.seen[0].headers


def test_a_body_with_no_declared_length_under_the_cap_is_read() -> None:
    with LocalServer(lambda r: page("a" * 500, "text/plain", **{"x-omit-length": "1"})) as server:
        assert len(fetcher(max_bytes=1000)[0].fetch(server.url).text) == 500


# ------------------------------------------------------------------------ the pinned address
def test_the_request_goes_to_the_vetted_address_and_asks_for_the_name_that_was_written() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, html="<p>hello</p>")

    class Pins(OutboundUrlPinnerInterface):
        def pin(self, url: str) -> PinDecision:
            return PinDecision.pinned(
                PinnedTarget(
                    "https://93.184.216.34:8443/a?x=1", "bees.example:8443", "bees.example"
                )
            )

    fetch = HttpSourceFetcher(
        httpx.Client(transport=httpx.MockTransport(handler)), Pins(), HtmlTextExtractor()
    )
    found = fetch.fetch("https://bees.example:8443/a?x=1")
    [request] = seen
    assert str(request.url) == "https://93.184.216.34:8443/a?x=1"
    assert request.headers["host"] == "bees.example:8443"
    assert request.extensions["sni_hostname"] == "bees.example"
    assert found.url == "https://bees.example:8443/a?x=1" and found.text == "hello"


def test_every_request_closes_its_connection_so_one_verified_for_a_name_is_not_reused_for_another() -> (
    None
):
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, html="<p>x</p>")

    fetch = HttpSourceFetcher(
        httpx.Client(transport=httpx.MockTransport(handler)), Pinner(), HtmlTextExtractor()
    )
    fetch.fetch("https://a.example/x")
    assert seen[0].headers["connection"] == "close"


def test_a_redirect_is_pinned_again_for_the_name_it_names_and_the_original_name_is_the_base() -> (
    None
):
    seen: list[httpx.Request] = []

    class Pins(OutboundUrlPinnerInterface):
        def __init__(self) -> None:
            self.asked: list[str] = []

        def pin(self, url: str) -> PinDecision:
            self.asked.append(url)
            host = urlsplit(url).hostname or ""
            address = {"a.example": "93.184.216.1", "b.example": "93.184.216.2"}[host]
            return PinDecision.pinned(PinnedTarget(f"https://{address}/p", host, host))

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.host == "93.184.216.1":
            return httpx.Response(302, headers={"location": "https://b.example/p"})
        return httpx.Response(200, html="<p>arrived</p>")

    pins = Pins()
    fetch = HttpSourceFetcher(
        httpx.Client(transport=httpx.MockTransport(handler)), pins, HtmlTextExtractor()
    )
    found = fetch.fetch("https://a.example/p")
    assert pins.asked == ["https://a.example/p", "https://b.example/p"]
    assert [r.url.host for r in seen] == ["93.184.216.1", "93.184.216.2"]
    assert [r.headers["host"] for r in seen] == ["a.example", "b.example"]
    assert found.url == "https://b.example/p"


def test_a_name_that_resolves_public_and_then_inward_is_sent_to_the_public_address_only() -> None:
    answers = iter([["93.184.216.34"], ["10.0.0.5"]])
    sent: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request.url.host)
        return httpx.Response(200, html="<p>ok</p>")

    pinner = PublicHttpsUrlPinner(PublicHttpsUrlPolicy(), lambda host: next(answers))
    fetch = HttpSourceFetcher(
        httpx.Client(transport=httpx.MockTransport(handler)), pinner, HtmlTextExtractor()
    )
    assert fetch.fetch("https://rebind.example/x").text == "ok"
    assert sent == ["93.184.216.34"]
