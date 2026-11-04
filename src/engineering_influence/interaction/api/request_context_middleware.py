# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pure-ASGI middleware: correlation id, request counters and the response header."""

import time
from collections.abc import MutableMapping
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from engineering_influence.domain.trace_context import TraceContext
from engineering_influence.interfaces.correlation_port import CorrelationPort
from engineering_influence.interfaces.metrics_port import MetricsPort

_QUIET = frozenset({"/health/live", "/health/ready", "/metrics"})


class RequestContextMiddleware:
    """Give every HTTP request one correlation id, count it, and return the id to the caller.

    This is plain ASGI rather than ``BaseHTTPMiddleware`` so the id is set in the same
    context that the route handlers run in.
    """

    def __init__(self, app: ASGIApp, correlation: CorrelationPort, metrics: MetricsPort) -> None:
        self.app = app
        self._correlation = correlation
        self._metrics = metrics

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Wrap one request."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {
            key.decode("latin-1"): value.decode("latin-1") for key, value in scope["headers"]
        }
        correlation_id = TraceContext.resolve_correlation_id(
            headers.get("traceparent"), headers.get("x-request-id")
        )
        quiet = scope["path"] in _QUIET
        outcome: MutableMapping[str, Any] = {"status": 500}

        async def respond(message: Message) -> None:
            if message["type"] == "http.response.start":
                outcome["status"] = message["status"]
                message = {
                    **message,
                    "headers": [
                        *message.get("headers", []),
                        (b"x-request-id", correlation_id.encode()),
                    ],
                }
            await send(message)

        started = time.monotonic()
        with self._correlation.scope(correlation_id):
            try:
                await self.app(scope, receive, respond)
            except Exception:
                if not quiet:
                    self._metrics.increment("http.exceptions")
                raise
            finally:
                if not quiet:
                    self._count(outcome["status"], time.monotonic() - started)

    def _count(self, status: int, elapsed_seconds: float) -> None:
        self._metrics.increment("http.requests")
        self._metrics.increment(f"http.status.{status // 100}xx")
        self._metrics.increment("http.request_ms", int(elapsed_seconds * 1000))
