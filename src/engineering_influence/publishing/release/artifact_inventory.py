"""The files a release must produce, with sizes and hashes."""

from pathlib import Path
from typing import Any

from engineering_influence.publishing.path_relativizer import PathRelativizer
from engineering_influence.publishing.project_layout import ProjectLayout
from engineering_influence.publishing.release.file_digest import FileDigest


class ArtifactInventory:
    """Lists required artifacts and reports the ones that are missing."""

    def __init__(self, layout: ProjectLayout) -> None:
        self._layout = layout
        self._relativizer = PathRelativizer(layout.root)

    def artifacts(self, slug: str, *, hardcover: bool = False) -> list[dict[str, Any]]:
        """The required artifacts for the book, each with existence, size, and hash."""
        output = self._layout.output
        covers = output / "covers" / slug
        required = [
            (output / f"{slug}.pdf", "pdf-interior"),
            (output / f"{slug}.epub", "epub"),
            (covers / f"{slug}-ebook.jpg", "ebook-cover"),
            (covers / f"{slug}-paperback-wrap.pdf", "paperback-wrap"),
            (covers / f"{slug}-hardcover-wrap.pdf", "hardcover-wrap"),
        ]
        if hardcover:
            required.insert(1, (output / f"{slug}-hardcover.pdf", "hardcover-interior"))
        return [self._artifact(path, kind) for path, kind in required]

    def problems(self, artifacts: list[dict[str, Any]]) -> list[str]:
        """A problem for each artifact that does not exist."""
        return [f"missing artifact: {item['path']}" for item in artifacts if not item["exists"]]

    def _artifact(self, path: Path, kind: str) -> dict[str, Any]:
        item: dict[str, Any] = {
            "kind": kind,
            "path": self._relativizer.relative(path),
            "exists": path.exists(),
        }
        if path.exists():
            item["bytes"] = path.stat().st_size
            item["sha256"] = FileDigest().sha256(path)
        return item
