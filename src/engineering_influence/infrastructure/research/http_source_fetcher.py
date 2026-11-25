# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Fetches a web page as evidence, refusing anything the policy does not allow, at every hop."""

from urllib.parse import urljoin, urlsplit

import httpx

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.outbound_url_pinner_interface import (
    OutboundUrlPinnerInterface,
)
from engineering_influence.interfaces.page_text_extractor_interface import (
    PageTextExtractorInterface,
)
from engineering_influence.interfaces.source_fetcher_interface import SourceFetcherInterface
from engineering_influence.models.fetched_page import FetchedPage
from engineering_influence.models.pinned_target import PinnedTarget


class HttpSourceFetcher(SourceFetcherInterface):
    """One GET per hop, with no cookies and no credentials, and a limit on every dimension.

    - **Where it may go** is the injected pinner's decision, asked before the first request and
      again before each redirect, so a page cannot send the fetcher inward by redirecting. A
      scheme other than http or https is refused here before the client sees it. Redirects are
      followed by hand, up to ``max_redirects``.
    - **It connects to the address that was checked.** The pinner resolves the name once and hands
      back the vetted address; the request goes to that address with the name in the ``Host`` header
      and in TLS, so the certificate is still checked against the name. A name that resolves
      differently a moment later cannot send the request inward (DNS rebinding). Each request also
      says ``Connection: close``, so a connection verified for one name is never reused for another
      that happens to share the address.
    - **How much it reads** is capped: a declared length over the cap is refused before any of
      the body is read, and reading stops at the cap. Compression is not accepted at all (the
      request asks for ``identity`` and any other ``content-encoding`` is refused), because a
      decoder expands each chunk in full before a byte count can see it, so a small download
      could fill memory. The cost is that a server that insists on compressing is not read.
    - **What it accepts** is HTML and plain text. A PDF or an image is refused.
    - **What it sends** is a generic user agent and no identity. The client it is given must not
      carry credentials or cookies of its own.
    - **A failure** is an ApplicationError with a SOURCE_* code when the page cannot be used, and
      a TransientStageError (a timeout, a dropped connection, 429, 5xx) when trying again could
      work. Messages name the host, never the full address, which may carry a token.

    A proxy named in the environment, if any, receives the address and not the name.
    """

    USER_AGENT = "engineering-influence-source-fetcher"
    HTML_TYPES = frozenset({"text/html", "application/xhtml+xml"})
    PLAIN_TYPES = frozenset({"text/plain"})
    REDIRECTS = frozenset({301, 302, 303, 307, 308})
    SOURCE_NOT_FOUND = frozenset({404, 410})
    RETRYABLE = frozenset({408, 425, 429})

    def __init__(
        self,
        client: httpx.Client,
        pinner: OutboundUrlPinnerInterface,
        extractor: PageTextExtractorInterface,
        max_bytes: int = 2_000_000,
        max_redirects: int = 3,
    ) -> None:
        if max_bytes < 1 or max_redirects < 0:
            raise ValueError("limits must allow at least one byte and no negative redirects")
        self._client = client
        self._pinner = pinner
        self._extractor = extractor
        self._max_bytes = max_bytes
        self._max_redirects = max_redirects

    def fetch(self, url: str) -> FetchedPage:
        """The page, or an ApplicationError (a SOURCE_* code) when it cannot be used."""
        current = url
        for _ in range(self._max_redirects + 1):
            target = self._allow(current)
            host = urlsplit(current).hostname or "the host"
            try:
                with self._client.stream(
                    "GET",
                    target.url,
                    headers={
                        "user-agent": self.USER_AGENT,
                        "accept": "text/html,text/plain",
                        "accept-encoding": "identity",
                        "connection": "close",
                        **target.request_headers(),
                    },
                    extensions=target.request_extensions(),
                    follow_redirects=False,
                ) as response:
                    if response.status_code not in self.REDIRECTS:
                        return self._page(current, host, response)
                    current = self._next(current, host, response)
            except httpx.TransportError as error:
                raise TransientStageError(
                    f"{host} could not be reached: {type(error).__name__}"
                ) from error
        raise self._error(
            "SOURCE_TOO_MANY_REDIRECTS", f"{host} redirected more than {self._max_redirects} times"
        )

    def _allow(self, url: str) -> PinnedTarget:
        if urlsplit(url).scheme not in ("http", "https"):
            raise self._error("SOURCE_URL_REFUSED", "a source address must be http or https")
        decision = self._pinner.pin(url)
        if decision.target is None:
            host = urlsplit(url).hostname or "the host"
            raise self._error("SOURCE_URL_REFUSED", f"{host} refused: {decision.reason}")
        return decision.target

    def _next(self, current: str, host: str, response: httpx.Response) -> str:
        location = response.headers.get("location")
        if not location:
            raise self._error("SOURCE_UNAVAILABLE", f"{host} redirected without saying where")
        return str(urljoin(current, location))

    def _page(self, url: str, host: str, response: httpx.Response) -> FetchedPage:
        status = response.status_code
        if status in self.SOURCE_NOT_FOUND:
            raise self._error("SOURCE_NOT_FOUND", f"{host} answered {status}")
        if status in self.RETRYABLE or status >= 500:
            raise TransientStageError(f"{host} answered {status}")
        if status != 200:
            raise self._error("SOURCE_UNAVAILABLE", f"{host} answered {status}")
        kind = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if kind not in self.HTML_TYPES | self.PLAIN_TYPES:
            raise self._error(
                "SOURCE_UNSUPPORTED_TYPE", f"{host} sent {kind or 'no content type'}, not text"
            )
        encoding = response.headers.get("content-encoding", "identity").lower()
        if encoding not in ("", "identity"):
            raise self._error(
                "SOURCE_UNSUPPORTED_ENCODING",
                f"{host} sent a {encoding} body; only uncompressed pages are read",
            )
        declared = response.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > self._max_bytes:
            raise self._error("SOURCE_TOO_LARGE", f"{host} sent more than {self._max_bytes} bytes")
        body = bytearray()
        for chunk in response.iter_bytes():
            body.extend(chunk)
            if len(body) > self._max_bytes:
                raise self._error(
                    "SOURCE_TOO_LARGE", f"{host} sent more than {self._max_bytes} bytes"
                )
        content = self._decode(bytes(body), response.charset_encoding)
        found = (
            self._extractor.extract_html(content)
            if kind in self.HTML_TYPES
            else self._extractor.extract_plain(content)
        )
        if found.is_empty():
            raise self._error("SOURCE_EMPTY", f"{host} sent a page with no readable text")
        return FetchedPage(url, found.title, found.text)

    @staticmethod
    def _decode(data: bytes, charset: str | None) -> str:
        try:
            return data.decode(charset or "utf-8", errors="replace")
        except LookupError:
            return data.decode("utf-8", errors="replace")

    @staticmethod
    def _error(code: str, message: str) -> ApplicationError:
        return ApplicationError(code=code, message=message, http_status=422)
