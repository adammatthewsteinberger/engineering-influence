# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: whether what a stage wrote can be used by the stage that reads it."""

from __future__ import annotations

from abc import ABC, abstractmethod


class StageOutputCheckInterface(ABC):
    """Checks a stage's answer before it is stored, so a malformed one stops the run where it was written."""

    __slots__ = ()

    @abstractmethod
    def check(self, stage: str, text: str) -> None:
        """Return when the answer is usable; raise an ApplicationError saying what is wrong when it is not."""
