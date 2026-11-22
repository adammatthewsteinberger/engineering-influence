# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Stamps a development suffix onto the version of a copy of the source, for a TestPyPI build."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


class DevVersionStamper:
    """Rewrites ``__version__`` to ``<version>.dev<build>`` in the files it is given.

    A development version sorts before the release it is named for and after every earlier build
    of it, and a package index never accepts a version twice, so each build of ``develop`` needs
    a number of its own. The files are the ones of a staged copy of the commit: the checkout is
    never touched. Only a plain release version (``0.1.0a2``) is stamped; one that is already a
    development version is refused rather than stamped twice.
    """

    VERSION_LINE = re.compile(r'^__version__ = "([^"]+)"$', re.MULTILINE)
    RELEASE = re.compile(r"\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?")

    def stamp_all(self, paths: list[Path], build: str) -> str:
        """Stamp every file with the same result, or none of them; return the stamped version."""
        if not (build.isascii() and build.isdigit()) or len(build) > 18:
            raise ValueError(f"a build number is digits only, not {build!r}")
        if not paths:
            raise ValueError("there is no file to stamp")
        versions = {self._version(path) for path in paths}
        if len(versions) != 1:
            raise ValueError(f"the files carry different versions: {sorted(versions)}")
        stamped = f"{versions.pop()}.dev{int(build)}"
        for path in paths:
            text = path.read_text(encoding="utf-8")
            path.write_text(
                self.VERSION_LINE.sub(f'__version__ = "{stamped}"', text), encoding="utf-8"
            )
        return stamped

    def _version(self, path: Path) -> str:
        found = self.VERSION_LINE.findall(path.read_text(encoding="utf-8"))
        if len(found) != 1:
            raise ValueError(f"{path} must have exactly one __version__ line")
        if not self.RELEASE.fullmatch(found[0]):
            raise ValueError(f"{found[0]!r} in {path} is not a plain release version")
        return found[0]


def main(argv: list[str] | None = None) -> int:
    """Stamp the given files and print the stamped version."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", help="the build number, digits only (the workflow run number)")
    parser.add_argument("files", nargs="+", type=Path, help="files with a __version__ line")
    arguments = parser.parse_args(argv)
    try:
        print(DevVersionStamper().stamp_all(arguments.files, arguments.build))
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
