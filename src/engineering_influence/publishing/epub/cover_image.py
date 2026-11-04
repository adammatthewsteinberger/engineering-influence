"""The ebook's internal cover image."""

import io
from pathlib import Path

from PIL import Image

from engineering_influence.publishing.project_layout import ProjectLayout
from engineering_influence.publishing.typesetting.book import Book
from engineering_influence.publishing.typesetting.book_build_error import BookBuildError


class CoverImage:
    """The Kindle Publishing Guidelines require an internal cover declared in the OPF."""

    NAME = "cover.jpg"
    ID = "cover-image"
    MIN_PX = (1600, 2500)  # KDP wants a large cover; verification fails a smaller one

    def __init__(self, layout: ProjectLayout) -> None:
        self._layout = layout

    def source(self, book: Book) -> Path:
        """Where the cover builder leaves the ebook cover."""
        return self._layout.output / "covers" / book.slug / f"{book.slug}-ebook.jpg"

    def jpeg(self, book: Book) -> bytes:
        """The ebook cover, full size, re-encoded lighter for the per-megabyte delivery fee."""
        source = self.source(book)
        if not source.exists():
            raise BookBuildError(f"[{book.slug}] {source} not found: build the covers first")
        with Image.open(source) as image:
            buffer = io.BytesIO()
            image.convert("RGB").save(
                buffer, format="JPEG", quality=85, optimize=True, dpi=(300, 300)
            )
        return buffer.getvalue()
