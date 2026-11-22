# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Downloads a file over https from an address the URL policy allows, with no redirects and a limit on size and time."""

import time
from collections.abc import Callable
from urllib.parse import urlsplit

import httpx

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.errors.transient_stage_error import TransientStageError
from engineering_influence.interfaces.bundle_fetcher_interface import BundleFetcherInterface
from engineering_influence.interfaces.outbound_url_pinner_interface import (
    OutboundUrlPinnerInterface,
)


class HttpBundleFetcher(BundleFetcherInterface):
    """One GET, to the address that was checked, for a file whose bytes someone else will check.

    - **Where it may go** is the injected pinner's decision, asked before the request: https only, to a
      public address, never one on this machine or its network. The request is sent **to that address**,
      with the name in the ``Host`` header and in TLS, so a name that resolves differently a moment later
      cannot send it inward, and it says ``Connection: close`` so a connection verified for one name is
      never reused for another.
    - **A redirect is never followed**: a 3xx is an error that says so. An index cannot send this client,
      or what it reads, anywhere else; the address in the index is the address it fetches.
    - **How much it reads** is bounded on every side: a declared length over ``max_bytes`` is refused before
      the body is read, reading stops at the cap, compression is not accepted (a decoder would expand each
      chunk before a byte count could see it), and the whole download has ``request_seconds``.
    - **What it sends** is a generic user agent and nothing else: no cookies, no credentials.
    - It does **not** decide whether the bytes are what anyone wanted. It does not look at the content
      type or the content; the caller checks the hash before reading them as anything.

    A failure names the host, never the full address. A proxy named in the environment, if any, receives
    the address and not the name.
    """

    USER_AGENT = "engineering-influence-bundle-fetcher"
    RETRYABLE = frozenset({408, 425, 429})
    NOT_FOUND = frozenset({404, 410})

    def __init__(
        self,
        client: httpx.Client,
        pinner: OutboundUrlPinnerInterface,
        request_seconds: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if request_seconds <= 0:
            raise ValueError("a download gets some time")
        self._client = client
        self._pinner = pinner
        self._request_seconds = request_seconds
        self._clock = clock

    def fetch(self, url: str, max_bytes: int) -> bytes:
        """The file's bytes, at most ``max_bytes`` of them, or an ApplicationError (BUNDLE_*) saying why not."""
        if max_bytes < 1:
            raise ValueError("a download is at least one byte long")
        host = urlsplit(url).hostname or "the host"
        decision = self._pinner.pin(url)
        if decision.target is None:
            raise self._error("BUNDLE_URL_REFUSED", f"{host} refused: {decision.reason}", 422)
        target = decision.target
        deadline = self._clock() + self._request_seconds
        try:
            with self._client.stream(
                "GET",
                target.url,
                headers={
                    "user-agent": self.USER_AGENT,
                    "accept": "*/*",
                    "accept-encoding": "identity",
                    "connection": "close",
                    **target.request_headers(),
                },
                extensions=target.request_extensions(),
                follow_redirects=False,
            ) as response:
                self._check(host, response)
                return self._read(host, response, max_bytes, deadline)
        except httpx.TransportError as error:
            raise TransientStageError(
                f"{host} could not be reached: {type(error).__name__}"
            ) from error
        finally:
            self._client.cookies.clear()

    def _check(self, host: str, response: httpx.Response) -> None:
        status = response.status_code
        if status == 200:
            return
        if 300 <= status < 400:
            raise self._error(
                "BUNDLE_REDIRECT_REFUSED", f"{host} answered with a redirect, which is not followed"
            )
        if status in self.NOT_FOUND:
            raise self._error("BUNDLE_NOT_FOUND", f"{host} answered {status}")
        if status in self.RETRYABLE or status >= 500:
            raise TransientStageError(f"{host} answered {status}")
        raise self._error("BUNDLE_HTTP_ERROR", f"{host} answered {status}")

    def _read(self, host: str, response: httpx.Response, max_bytes: int, deadline: float) -> bytes:
        encoding = response.headers.get("content-encoding", "identity").strip().lower()
        if encoding not in ("", "identity"):
            raise self._error(
                "BUNDLE_REPLY_INVALID",
                f"{host} sent a {encoding[:20]!r} body; only uncompressed files are read",
            )
        declared = response.headers.get("content-length", "")
        if declared.isdigit() and int(declared) > max_bytes:
            raise self._error("BUNDLE_TOO_LARGE", f"{host} sent more than {max_bytes} bytes")
        body = bytearray()
        for chunk in response.iter_bytes():
            body.extend(chunk)
            if len(body) > max_bytes:
                raise self._error("BUNDLE_TOO_LARGE", f"{host} sent more than {max_bytes} bytes")
            if self._clock() > deadline:
                raise TransientStageError(
                    f"{host} did not finish sending in {self._request_seconds:g} seconds"
                )
        return bytes(body)

    @staticmethod
    def _error(code: str, message: str, status: int = 502) -> ApplicationError:
        return ApplicationError(code=code, message=message, http_status=status)
