# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One thing the doctor checked about a model profile."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.doctor_finding_interface import (
    DoctorFindingInterface,
)


@dataclass(frozen=True, slots=True)
class DoctorFinding(DoctorFindingInterface):
    """A check on one profile and its result.

    ``detail`` is shown to the user and may end up in a log, so a finding must never carry a key.
    """

    profile: str
    check: str
    passed: bool
    detail: str

    def line(self) -> str:
        """``ok`` or ``FAIL``, then the profile, the check and what was found."""
        mark = "ok  " if self.passed else "FAIL"
        return f"{mark} {self.profile}: {self.check}: {self.detail}"
