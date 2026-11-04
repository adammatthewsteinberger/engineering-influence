# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""EPUB container rules: intact ZIP, mimetype first and stored."""

import zipfile
from pathlib import Path


class EpubZipCheck:
    """Structural checks that do not need to parse any content."""

    def run(self, path: Path) -> list[str]:
        """Return problems with the archive itself."""
        if not path.exists():
            return [f"missing EPUB for ZIP validation: {path}"]
        try:
            with zipfile.ZipFile(path) as archive:
                bad = archive.testzip()
                if bad:
                    return [f"EPUB ZIP integrity failed at {bad}"]
                names = archive.namelist()
                if not names or names[0] != "mimetype":
                    return ["EPUB ZIP must keep mimetype as its first member"]
                if archive.getinfo("mimetype").compress_type != zipfile.ZIP_STORED:
                    return ["EPUB mimetype member must be uncompressed"]
        except (OSError, zipfile.BadZipFile, KeyError) as error:
            return [f"EPUB ZIP validation failed: {error}"]
        return []
