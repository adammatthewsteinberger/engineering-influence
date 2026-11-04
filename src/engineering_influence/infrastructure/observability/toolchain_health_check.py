# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Check that the executables book building needs are installed."""

import shutil
from collections.abc import Callable

from engineering_influence.contracts.health_status import HealthStatus
from engineering_influence.interfaces.health_check_port import HealthCheckPort


class ToolchainHealthCheck(HealthCheckPort):
    """Healthy when every required executable is on the PATH."""

    def __init__(
        self,
        executables: tuple[str, ...] = ("lualatex", "latexmk"),
        locator: Callable[[str], str | None] = shutil.which,
        name: str = "tex-toolchain",
    ) -> None:
        self._executables = executables
        self._locate = locator
        self._name = name

    @property
    def name(self) -> str:
        """Return the check name."""
        return self._name

    def check(self) -> HealthStatus:
        """List which executables are missing."""
        missing = [item for item in self._executables if self._locate(item) is None]
        if missing:
            return HealthStatus(
                name=self._name, healthy=False, detail="missing: " + ", ".join(missing)
            )
        return HealthStatus(name=self._name, healthy=True)
