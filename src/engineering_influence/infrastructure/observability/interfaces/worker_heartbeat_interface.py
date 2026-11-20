# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for WorkerHeartbeat."""

from abc import ABC, abstractmethod


class WorkerHeartbeatInterface(ABC):
    """Log a heartbeat and alert when the worker stops making progress."""

    __slots__ = ()

    @abstractmethod
    def record_progress(self) -> None:
        """Call whenever the worker handles or settles a job."""

    @abstractmethod
    def check_silence(self) -> bool:
        """Raise an alert when progress has stalled; return whether one was raised."""

    @abstractmethod
    def start(self) -> None:
        """Start the heartbeat and watchdog threads."""

    @abstractmethod
    def stop(self) -> None:
        """Stop both threads and wait for them."""
