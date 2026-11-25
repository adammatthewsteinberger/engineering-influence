# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""A small HTTP server on 127.0.0.1, for tests that need a real socket and a record of what it got."""

import threading
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import TracebackType
from typing import Self


@dataclass(frozen=True)
class Seen:
    """One request, as the server received it."""

    method: str
    target: str
    headers: dict[str, str]
    body: bytes

    def path(self) -> str:
        return self.target.split("?", 1)[0]


Reply = tuple[int, dict[str, str], bytes]


class _Quiet(ThreadingHTTPServer):
    def handle_error(self, request: object, client_address: object) -> None:
        return  # a client that hangs up mid-reply is part of some tests


class LocalServer:
    """Answers every request from ``route`` and keeps each one in ``seen``."""

    def __init__(self, route: Callable[[Seen], Reply]) -> None:
        self.seen: list[Seen] = []
        self._route = route
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        assert self._server is not None
        return f"http://127.0.0.1:{self._server.server_port}"

    def __enter__(self) -> Self:
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def _serve(self) -> None:
                length = int(self.headers.get("content-length") or 0)
                request = Seen(
                    self.command,
                    self.path,
                    {key.lower(): value for key, value in self.headers.items()},
                    self.rfile.read(length) if length else b"",
                )
                owner.seen.append(request)
                status, headers, body = owner._route(request)
                self.send_response(status)
                names = {name.lower() for name in headers}
                for name, value in headers.items():
                    if name.lower() != "x-omit-length":
                        self.send_header(name, value)
                if not {"content-length", "x-omit-length"} & names:
                    self.send_header("content-length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            do_GET = do_POST = do_DELETE = do_PUT = _serve

            def log_message(self, format: str, *args: object) -> None:
                return

        self._server = _Quiet(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(
            target=lambda: self._server.serve_forever(poll_interval=0.01), daemon=True
        )
        self._thread.start()
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        error: BaseException | None,
        trace: TracebackType | None,
    ) -> None:
        assert self._server is not None and self._thread is not None
        self._server.shutdown()
        self._server.server_close()
        self._thread.join()
