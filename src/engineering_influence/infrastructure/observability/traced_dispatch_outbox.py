# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tracing decorator for the outbox dispatch service."""

from vibey_bootstrap.tracing.decorators import traced_async

from engineering_influence.services.interfaces.dispatch_outbox_interface import (
    DispatchOutboxInterface,
)


class TracedDispatchOutbox(DispatchOutboxInterface):
    """Record latency and errors for every drain; the argument is the signing secret."""

    def __init__(self, inner: DispatchOutboxInterface) -> None:
        self._inner = inner

    @traced_async(operation="service.dispatch_outbox", sensitive_args=("secret",))
    async def dispatch(self, secret: bytes) -> int:
        """Delegate to the wrapped service."""
        return await self._inner.dispatch(secret)
