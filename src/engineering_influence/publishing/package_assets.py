"""The LaTeX classes, stylesheet, and fonts that ship inside the package."""

from contextlib import AbstractContextManager
from importlib.resources import as_file, files
from pathlib import Path


class PackageAssets:
    """Locates the bundled assets as a real directory, even from a zipped install."""

    def directory(self) -> AbstractContextManager[Path]:
        """Context manager yielding the assets directory.

        It holds fine-book.cls, fine-book-hardcover.cls, fine-ebook.sty, fine-ebook.cfg,
        fine-ebook.css, and fonts/ with the license of every font.
        """
        return as_file(files("engineering_influence.publishing") / "assets")
