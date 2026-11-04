"""Express paths relative to a project root."""

from pathlib import Path


class PathRelativizer:
    """Reports stable root-relative paths, falling back to the absolute path."""

    def __init__(self, root: Path) -> None:
        self._root = root.resolve()

    def relative(self, path: Path) -> str:
        """Return the path relative to the root, or absolute when it lies outside."""
        resolved = path.resolve()
        try:
            return str(resolved.relative_to(self._root))
        except ValueError:
            return str(resolved)
