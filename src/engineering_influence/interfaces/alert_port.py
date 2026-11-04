# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Alert port."""

from abc import ABC, abstractmethod


class AlertPort(ABC):
    """Raise an operator alert that must never be lost silently."""

    @abstractmethod
    def raise_alert(
        self, severity: str, subject: str, context: dict[str, object], dedup_key: str
    ) -> None:
        """Record an alert; repeated alerts with the same dedup key are counted, not repeated."""
