"""Directory conventions of a publishing project."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ProjectLayout:
    """Where a project keeps book configs, build products, and finished outputs."""

    root: Path

    @property
    def books(self) -> Path:
        """Per-book TOML configuration files."""
        return self.root / "books"

    @property
    def build(self) -> Path:
        """Scratch directory for generated sources and logs."""
        return self.root / "build"

    @property
    def output(self) -> Path:
        """Finished PDFs and EPUBs."""
        return self.root / "output"
