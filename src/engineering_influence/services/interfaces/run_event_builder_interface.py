# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for RunEventBuilder."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.book_run import BookRun
    from engineering_influence.models.outbox_event import OutboxEvent


class RunEventBuilderInterface(ABC):
    """The webhook events a run's transitions produce, one per configured receiver."""

    __slots__ = ()

    @abstractmethod
    def started(self, run: BookRun) -> tuple[OutboxEvent, ...]:
        """The run has started: pipeline.started."""

    @abstractmethod
    def phase_completed(self, run: BookRun, stage: str) -> tuple[OutboxEvent, ...]:
        """A stage has finished: phase.completed."""

    @abstractmethod
    def awaiting_gate(self, run: BookRun, stage: str) -> tuple[OutboxEvent, ...]:
        """The run waits for a decision: gate.awaiting."""

    @abstractmethod
    def completed(self, run: BookRun) -> tuple[OutboxEvent, ...]:
        """The run has finished every stage: pipeline.completed."""
