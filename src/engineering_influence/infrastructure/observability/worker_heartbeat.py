# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Worker liveness: a periodic heartbeat log and a silence watchdog."""

import threading
import time
from collections.abc import Callable
from typing import Any

from vibey_bootstrap.heartbeat import start_heartbeat

from engineering_influence.interfaces.alert_port import AlertPort
from engineering_influence.interfaces.metrics_port import MetricsPort


class WorkerHeartbeat:
    """Log a heartbeat and alert when the worker stops making progress.

    vibey_bootstrap's own watchdog words its alert for Azure Service Bus, raises an
    ERROR that waits in an undrained digest, and never fires when no iteration was ever
    recorded. This one counts from start, so a worker that never begins is caught.
    """

    def __init__(
        self,
        metrics: MetricsPort,
        alerts: AlertPort,
        heartbeat_seconds: float = 300.0,
        silence_seconds: float = 1800.0,
        check_seconds: float = 60.0,
        realert_seconds: float = 3600.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if min(heartbeat_seconds, silence_seconds, check_seconds, realert_seconds) <= 0:
            raise ValueError("every interval must be positive")
        self._metrics = metrics
        self._alerts = alerts
        self._heartbeat_seconds = heartbeat_seconds
        self._silence_seconds = silence_seconds
        self._check_seconds = check_seconds
        self._realert_seconds = realert_seconds
        self._clock = clock
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._lock = threading.Lock()
        self._last_progress = clock()
        self._last_alert: float | None = None

    def record_progress(self) -> None:
        """Call whenever the worker handles or settles a job."""
        with self._lock:
            self._last_progress = self._clock()

    def check_silence(self) -> bool:
        """Raise an alert when progress has stalled; return whether one was raised."""
        now = self._clock()
        with self._lock:
            silent_for = now - self._last_progress
            if silent_for <= self._silence_seconds:
                return False
            if self._last_alert is not None and now - self._last_alert < self._realert_seconds:
                return False
            self._last_alert = now
        self._alerts.raise_alert(
            "critical",
            "worker is not making progress",
            {"silent_seconds": int(silent_for), "threshold_seconds": int(self._silence_seconds)},
            "worker:silent",
        )
        return True

    def start(self) -> None:
        """Start the heartbeat and watchdog threads."""
        if self._threads:
            raise RuntimeError("heartbeat already started")
        self._stop.clear()
        self.record_progress()
        self._threads = [
            start_heartbeat(
                self._stop, interval_seconds=self._heartbeat_seconds, snapshot_fn=self._snapshot
            ),
            threading.Thread(target=self._watch, name="worker-watchdog", daemon=True),
        ]
        self._threads[1].start()

    def stop(self) -> None:
        """Stop both threads and wait for them."""
        self._stop.set()
        for thread in self._threads:
            thread.join(timeout=5)
        self._threads = []

    def _watch(self) -> None:
        while not self._stop.wait(self._check_seconds):
            self.check_silence()

    def _snapshot(self) -> dict[str, Any]:
        return {
            "counters": self._metrics.counters(),
            "latency_snapshot": self._metrics.latencies(),
        }
