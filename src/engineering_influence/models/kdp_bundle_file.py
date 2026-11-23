# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One finished file in a release bundle: what it is, its name in the bundle, and where it comes from."""

from dataclasses import dataclass
from pathlib import Path

from engineering_influence.models.interfaces.kdp_bundle_file_interface import (
    KdpBundleFileInterface,
)


@dataclass(frozen=True, slots=True)
class KdpBundleFile(KdpBundleFileInterface):
    """A finished file, with its kind (``pdf-interior``, ``epub``, ...), its size and its SHA-256."""

    kind: str
    name: str
    source: Path
    size: int
    sha256: str

    def __post_init__(self) -> None:
        if not self.name or "/" in self.name or "\\" in self.name or self.name in (".", ".."):
            raise ValueError("a bundle file is named by a plain filename")
        if self.size < 0 or len(self.sha256) != 64:
            raise ValueError("a bundle file has a size and a SHA-256")
