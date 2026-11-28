# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Folds changelog.d fragments into a new CHANGELOG.md section before a release."""

import argparse
import re
import sys
from pathlib import Path

UNRELEASED = "## Unreleased"
VERSION = re.compile(r"\d+\.\d+\.\d+(?:(?:a|b|rc)\d+)?(?:\.dev\d+)?")


class ChangelogFolder:
    """Turns the Unreleased section plus every fragment into a section named for a version."""

    def __init__(self, root: Path) -> None:
        """Remember the repository root whose changelog and fragments are folded."""
        self._changelog = root / "CHANGELOG.md"
        self._fragments = root / "changelog.d"

    def fragment_paths(self) -> list[Path]:
        """Every fragment, in file-name order; the README is not a fragment."""
        return sorted(p for p in self._fragments.glob("*.md") if p.name != "README.md")

    def fold(self, version: str) -> int:
        """Rewrite the changelog and delete the fragments; return how many were folded."""
        if not VERSION.fullmatch(version):
            raise ValueError(f"not a version: {version!r}")
        text = self._changelog.read_text(encoding="utf-8")
        if UNRELEASED not in text:
            raise ValueError(f"CHANGELOG.md has no '{UNRELEASED}' section")
        if re.search(rf"^## \[?{re.escape(version)}\]?( |$)", text, re.MULTILINE):
            raise ValueError(f"CHANGELOG.md already has a section for {version}")
        paths = self.fragment_paths()
        bullets = [f"- {path.read_text(encoding='utf-8').strip()}\n" for path in paths]
        head, _, rest = text.partition(f"{UNRELEASED}\n")
        existing = rest.lstrip("\n")
        folded = "".join(bullets)
        body = folded + existing if existing.startswith("- ") else folded + "\n" + existing
        self._changelog.write_text(
            f"{head}{UNRELEASED}\n\n## {version}\n\n{body}", encoding="utf-8"
        )
        for path in paths:
            path.unlink()
        return len(paths)


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    arguments = parser.parse_args(argv)
    try:
        count = ChangelogFolder(arguments.root).fold(arguments.version)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    print(f"folded {count} fragment(s) into {arguments.version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
