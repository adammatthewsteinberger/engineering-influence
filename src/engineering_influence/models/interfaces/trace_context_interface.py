# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for TraceContext."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.trace_context import TraceContext


class TraceContextInterface(ABC):
    """A W3C ``traceparent`` identity: one trace, one span."""

    __slots__ = ()

    @classmethod
    @abstractmethod
    def parse(cls, header: str | None) -> TraceContext | None:
        """Return the context from a ``traceparent`` header, or None when invalid."""

    @classmethod
    @abstractmethod
    def for_correlation_id(cls, correlation_id: str | None) -> TraceContext | None:
        """Return a fresh span in the trace named by the id, when the id is a valid trace id."""

    @classmethod
    @abstractmethod
    def resolve_correlation_id(cls, traceparent: str | None, request_id: str | None) -> str:
        """Pick a safe correlation id: the trace id, else a well-formed request id, else new."""

    @abstractmethod
    def header(self) -> str:
        """Return the ``traceparent`` header value."""
