# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port: the mechanical checks on a screenplay's source audit."""

from abc import ABC, abstractmethod


class ScreenplayAuditCheckInterface(ABC):
    """The mechanical checks on the source audit (prompt 08, step 8b)."""

    __slots__ = ()

    @abstractmethod
    def problems(self, text: str) -> tuple[str, ...]:
        """Every way the audit breaks the format, or nothing when it passes."""
