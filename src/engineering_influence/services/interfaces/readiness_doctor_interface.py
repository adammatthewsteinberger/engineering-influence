# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ReadinessDoctor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.doctor_finding import DoctorFinding


class ReadinessDoctorInterface(ABC):
    """Checks what a book needs on this machine before a run starts: the extras, the tools and the author's details."""

    __slots__ = ()

    @abstractmethod
    def check(self, profile: Path | None) -> tuple[DoctorFinding, ...]:
        """One finding for each extra, each tool and the author profile; nothing is sent anywhere."""
