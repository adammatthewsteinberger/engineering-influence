# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Prometheus text exposition of counters, latencies and dependency status."""

import re

from engineering_influence.contracts.readiness_report import ReadinessReport

_INVALID = re.compile(r"[^a-zA-Z0-9_]")
_QUANTILES = (("p50", "0.5"), ("p95", "0.95"), ("p99", "0.99"))


class PrometheusRenderer:
    """Render the text format (version 0.0.4) that Prometheus and compatible agents scrape."""

    def render(
        self,
        counters: dict[str, int],
        latencies: dict[str, dict[str, float]],
        readiness: ReadinessReport | None,
    ) -> str:
        """Return the exposition text; names are prefixed and sanitised, labels escaped."""
        lines: list[str] = []
        for name, value in sorted(counters.items()):
            metric = f"ei_{self._name(name)}_total"
            lines += [f"# TYPE {metric} counter", f"{metric} {value}"]
        if latencies:
            lines.append("# TYPE ei_operation_latency_seconds summary")
        for operation, stats in sorted(latencies.items()):
            label = self._label(operation)
            for key, quantile in _QUANTILES:
                if key in stats:
                    lines.append(
                        f'ei_operation_latency_seconds{{operation="{label}",'
                        f'quantile="{quantile}"}} {stats[key]}'
                    )
            lines.append(
                f'ei_operation_latency_seconds_count{{operation="{label}"}} {stats.get("count", 0)}'
            )
            lines.append(
                f'ei_operation_errors_total{{operation="{label}"}} {stats.get("errors", 0)}'
            )
        if readiness is not None:
            lines += ["# TYPE ei_ready gauge", f"ei_ready {int(readiness.ready)}"]
            lines.append("# TYPE ei_dependency_up gauge")
            for check in readiness.checks:
                lines.append(
                    f'ei_dependency_up{{name="{self._label(check.name)}"}} {int(check.healthy)}'
                )
        return "\n".join(lines) + "\n"

    @staticmethod
    def _name(raw: str) -> str:
        return _INVALID.sub("_", raw)

    @staticmethod
    def _label(raw: str) -> str:
        return raw.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
