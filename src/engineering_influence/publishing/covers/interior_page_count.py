# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Page count of a built interior PDF, which fixes the spine width."""

from pathlib import Path

from pypdf import PdfReader

from engineering_influence.publishing.typesetting.book_build_error import BookBuildError


class InteriorPageCount:
    """Reads the finished interior, never an estimate."""

    def of(self, pdf: Path) -> int:
        """The number of pages, or an error telling you to build the interior first."""
        if not pdf.exists():
            raise BookBuildError(f"{pdf} not found: build the interior first")
        return len(PdfReader(str(pdf)).pages)
