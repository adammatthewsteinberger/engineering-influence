# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for JobMessage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.contracts.job_message import JobMessage


class JobMessageInterface(ABC):
    """The broker message body: an id, a kind such as ``pipeline.thesis``, and a payload."""

    __slots__ = ()

    @classmethod
    @abstractmethod
    def parse(cls, body: bytes) -> JobMessage:
        """Validate raw bytes; anything malformed raises ``pydantic.ValidationError``."""
