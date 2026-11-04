# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A hardcover interior must stay under the configured page maximum."""

from pathlib import Path

from pypdf import PdfReader


class PageLimitCheck:
    """Compares a built interior's page count with the limit."""

    def run(self, path: Path, *, label: str, maximum: int) -> str | None:
        """A problem when the PDF exists and is too long; None otherwise."""
        if not path.exists():
            return None
        pages = len(PdfReader(str(path)).pages)
        if pages > maximum:
            return f"{label} has {pages} pages; configured maximum is {maximum}"
        return None
