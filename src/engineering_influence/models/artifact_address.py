# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Where an artifact lives: the run that made it and its name within that run."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.artifact_address_interface import (
    ArtifactAddressInterface,
)

RESERVED_SUFFIX = ".part"


@dataclass(frozen=True, slots=True)
class ArtifactAddress(ArtifactAddressInterface):
    """A run id and an artifact name such as ``draft/chapter-01.md``; names may nest, never climb."""

    run_id: str
    name: str

    def __post_init__(self) -> None:
        """Refuse a run id or artifact name that is empty or climbs out of its folder."""
        if self.run_id in ("", ".", "..") or not self.run_id.strip():
            raise ValueError("a run id is required and cannot contain a path separator")
        if "/" in self.run_id or "\\" in self.run_id:
            raise ValueError("a run id is required and cannot contain a path separator")
        if "\\" in self.name or any(part in ("", ".", "..") for part in self.name.split("/")):
            raise ValueError("an artifact name must be a relative path that stays inside the run")
        if self.name.endswith(RESERVED_SUFFIX):
            raise ValueError(f"artifact names cannot end in {RESERVED_SUFFIX}")

    def relative_path(self) -> str:
        """The address as ``run_id/name``, with forward slashes."""
        return f"{self.run_id}/{self.name}"
