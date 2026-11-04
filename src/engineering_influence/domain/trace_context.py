# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""W3C trace context and correlation-id resolution."""

import re
import secrets
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class TraceContext:
    """A W3C ``traceparent`` identity: one trace, one span."""

    trace_id: str
    span_id: str

    _TRACEPARENT: ClassVar[re.Pattern[str]] = re.compile(
        r"^00-(?P<trace>[0-9a-f]{32})-(?P<span>[0-9a-f]{16})-[0-9a-f]{2}$"
    )
    _REQUEST_ID: ClassVar[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
    _TRACE_ID: ClassVar[re.Pattern[str]] = re.compile(r"^[0-9a-f]{32}$")

    @classmethod
    def parse(cls, header: str | None) -> "TraceContext | None":
        """Return the context from a ``traceparent`` header, or None when invalid."""
        match = cls._TRACEPARENT.match(header.strip()) if header else None
        if match is None:
            return None
        trace, span = match.group("trace"), match.group("span")
        if set(trace) == {"0"} or set(span) == {"0"}:
            return None
        return cls(trace, span)

    @classmethod
    def for_correlation_id(cls, correlation_id: str | None) -> "TraceContext | None":
        """Return a fresh span in the trace named by the id, when the id is a valid trace id."""
        if not correlation_id or not cls._TRACE_ID.match(correlation_id):
            return None
        if set(correlation_id) == {"0"}:
            return None
        return cls(correlation_id, secrets.token_hex(8))

    @classmethod
    def resolve_correlation_id(cls, traceparent: str | None, request_id: str | None) -> str:
        """Pick a safe correlation id: the trace id, else a well-formed request id, else new.

        An inbound request id is attacker-controlled and ends up in every log line, so
        anything outside a short, plain alphabet is replaced rather than echoed.
        """
        context = cls.parse(traceparent)
        if context is not None:
            return context.trace_id
        if request_id and cls._REQUEST_ID.match(request_id):
            return request_id
        return secrets.token_hex(16)

    def header(self) -> str:
        """Return the ``traceparent`` header value."""
        return f"00-{self.trace_id}-{self.span_id}-01"
