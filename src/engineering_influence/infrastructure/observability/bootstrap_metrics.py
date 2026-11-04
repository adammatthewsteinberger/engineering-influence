# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Process-local counters and latency statistics from vibey_bootstrap."""

from vibey_bootstrap.counters import bump_counter, counter_snapshot
from vibey_bootstrap.tracing.latency import latency_snapshot

from engineering_influence.interfaces.metrics_port import MetricsPort


class BootstrapMetrics(MetricsPort):
    """Counters and latencies are process-local; scrape each replica separately."""

    def increment(self, name: str, amount: int = 1) -> None:
        """Add to a named counter."""
        bump_counter(name, amount)

    def counters(self) -> dict[str, int]:
        """Return every counter."""
        return counter_snapshot()

    def latencies(self) -> dict[str, dict[str, float]]:
        """Return latency statistics per traced operation."""
        return {
            operation: {
                key: float(value)
                for key, value in stats.items()
                if isinstance(value, (int, float)) and key != "last_seen"
            }
            for operation, stats in latency_snapshot().items()
        }
