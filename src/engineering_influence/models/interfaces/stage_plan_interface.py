# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for StagePlan."""

from abc import ABC, abstractmethod


class StagePlanInterface(ABC):
    """The ordered stages a run walks through for one kind of book."""

    __slots__ = ()

    @abstractmethod
    def first(self) -> str:
        """The stage a new run starts on."""

    @abstractmethod
    def after(self, stage: str) -> str | None:
        """The stage that follows ``stage``, or None after the last one."""
