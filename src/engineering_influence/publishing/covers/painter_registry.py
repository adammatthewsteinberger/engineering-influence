# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Named cover painters."""

from engineering_influence.publishing.covers.cover_painter import CoverPainter
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError


class PainterRegistry:
    """Maps the painter name in a style to the painter that draws it."""

    def __init__(self) -> None:
        self._painters: dict[str, CoverPainter] = {}

    def register(self, name: str, painter: CoverPainter) -> None:
        """Add a painter; a later registration under the same name replaces the earlier one."""
        self._painters[name] = painter

    def get(self, name: str) -> CoverPainter:
        """Return the painter, or fail with the names that are available."""
        try:
            return self._painters[name]
        except KeyError:
            known = ", ".join(sorted(self._painters)) or "none"
            raise BookBuildError(f"no cover painter named {name!r} (registered: {known})") from None
