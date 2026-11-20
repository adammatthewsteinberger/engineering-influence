# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A hardcover interior must stay under the configured page maximum."""

from pathlib import Path

from engineering_influence.interfaces.pdf_inspector_interface import PdfInspectorInterface


class PageLimitCheck:
    """Compares a built interior's page count with the limit."""

    def __init__(self, pdfs: PdfInspectorInterface) -> None:
        self._pdfs = pdfs

    def run(self, path: Path, *, label: str, maximum: int) -> str | None:
        """A problem when the PDF exists and is too long; None otherwise."""
        pages = self._pdfs.page_count(path)
        if pages is None:
            return None
        if pages > maximum:
            return f"{label} has {pages} pages; configured maximum is {maximum}"
        return None
