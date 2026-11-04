# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Correlation ids carried in a context variable."""

from contextlib import AbstractContextManager

from vibey_bootstrap.logging.correlation import correlation_scope, get_correlation_id

from engineering_influence.interfaces.correlation_port import CorrelationPort


class ContextVarCorrelation(CorrelationPort):
    """Correlation that follows async tasks and, with copied context, worker threads."""

    def current(self) -> str | None:
        """Return the active id."""
        return get_correlation_id()

    def scope(self, correlation_id: str | None) -> AbstractContextManager[str]:
        """Activate an id for the block; every log record inside carries it."""
        return correlation_scope(correlation_id)
