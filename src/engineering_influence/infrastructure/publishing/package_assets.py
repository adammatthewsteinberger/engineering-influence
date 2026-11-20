# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The LaTeX classes, stylesheet, and fonts that ship inside the package."""

from contextlib import AbstractContextManager, nullcontext
from importlib.resources import as_file, files
from pathlib import Path

from engineering_influence.interfaces.package_assets_interface import PackageAssetsInterface


class PackageAssets(PackageAssetsInterface):
    """Locates the bundled assets as a real directory, even from a zipped install.

    ``override`` serves a directory of your own instead, for a project with its own class files.
    """

    def __init__(self, override: Path | None = None) -> None:
        self._override = override

    def directory(self) -> AbstractContextManager[Path]:
        """Context manager yielding the assets directory.

        It holds fine-book.cls, fine-book-hardcover.cls, fine-ebook.sty, fine-ebook.cfg,
        fine-ebook.css, and fonts/ with the license of every font.
        """
        if self._override is not None:
            return nullcontext(self._override)
        return as_file(files("engineering_influence.publishing") / "assets")
