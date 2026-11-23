# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for LocalModelDoctor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.doctor_finding import DoctorFinding


class LocalModelDoctorInterface(ABC):
    """Checks that the free local model is ready: the server, the model, an answer and the context."""

    __slots__ = ()

    @abstractmethod
    def check(self) -> tuple[DoctorFinding, ...]:
        """One finding for each check that could be made, stopping at the first thing that makes the rest pointless."""
