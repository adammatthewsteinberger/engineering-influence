# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Port for the acceptance pipeline."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class PublishPipelineInterface(ABC):
    """Run a book through every gate and write the publication report."""

    __slots__ = ()

    @abstractmethod
    def publish(
        self,
        slug: str,
        *,
        dpi: int = 90,
        audit_only: bool = False,
        no_render: bool = False,
        report_path: Path | None = None,
        strict_release: bool = False,
    ) -> tuple[dict[str, Any], bool]:
        """Return (the report, whether every gate passed)."""
