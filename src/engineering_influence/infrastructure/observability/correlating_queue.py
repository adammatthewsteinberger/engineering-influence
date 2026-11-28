# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Queue decorator that carries the correlation id into every job."""

from engineering_influence.interfaces.correlation_interface import CorrelationInterface
from engineering_influence.interfaces.queue_interface import QueueInterface
from engineering_influence.models.trace_context import TraceContext


class CorrelatingQueue(QueueInterface):
    """Stamp ``correlation_id`` (and ``traceparent``) onto a copy of each payload."""

    def __init__(self, inner: QueueInterface, correlation: CorrelationInterface) -> None:
        """Remember the queue to publish to and the correlation that supplies the ids."""
        self._inner = inner
        self._correlation = correlation

    def enqueue(self, kind: str, payload: dict[str, object]) -> str:
        """Copy first: callers share the payload with the ledger, which must not change."""
        stamped = dict(payload)
        correlation_id = self._correlation.current()
        if correlation_id:
            stamped["correlation_id"] = correlation_id
            context = TraceContext.for_correlation_id(correlation_id)
            if context is not None:
                stamped["traceparent"] = context.header()
        return self._inner.enqueue(kind, stamped)
