# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for ModelDoctor."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from engineering_influence.models.doctor_finding import DoctorFinding


class ModelDoctorInterface(ABC):
    """Check that a deployment's model profiles are ready to be called."""

    __slots__ = ()

    @abstractmethod
    def check(self, catalog_path: Path, profiles_path: Path) -> tuple[DoctorFinding, ...]:
        """One finding per check per profile; a file that cannot be read raises ApplicationError."""
