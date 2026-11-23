# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for SearchDoctor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from engineering_influence.models.doctor_finding import DoctorFinding


class SearchDoctorInterface(ABC):
    """Checks that the web search the research stage depends on really answers."""

    __slots__ = ()

    @abstractmethod
    def check(self, query: str) -> tuple[DoctorFinding, ...]:
        """One finding per configured provider, from one real search each; nothing configured is one failed finding."""
