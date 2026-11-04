# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Worker handler decorator that restores the correlation id from the job."""

from typing import Any

from engineering_influence.interfaces.correlation_port import CorrelationPort
from engineering_influence.interfaces.phase_handler_port import PhaseHandlerPort


class CorrelatedPhaseHandler(PhaseHandlerPort):
    """Run the inner handler inside the id the job was queued with."""

    def __init__(self, inner: PhaseHandlerPort, correlation: CorrelationPort) -> None:
        self._inner = inner
        self._correlation = correlation

    async def handle(self, job: Any) -> Any:
        """A job queued without an id gets a new one, so its logs are still grouped."""
        queued = dict(job.payload).get("correlation_id")
        with self._correlation.scope(queued if isinstance(queued, str) else None):
            return await self._inner.handle(job)
