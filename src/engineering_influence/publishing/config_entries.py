# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Printed order of a book's configured files."""

from typing import Any


class ConfigEntries:
    """Flattens front matter, parts and chapters, and back matter."""

    def iterate(self, config: dict[str, Any]) -> list[tuple[str, str, str, int | None]]:
        """Return (kind, file, style, number) in printed order."""
        entries: list[tuple[str, str, str, int | None]] = []
        for item in config.get("front", []):
            entries.append(("front", self._file(item), self._style(item), None))
        number = 0
        for part in config.get("parts", []):
            for item in part.get("chapters", []):
                number += 1
                entries.append(("chapter", self._file(item), self._style(item), number))
        for item in config.get("back", []):
            entries.append(("back", self._file(item), self._style(item), None))
        return entries

    def _file(self, item: str | dict[str, Any]) -> str:
        return item if isinstance(item, str) else str(item["file"])

    def _style(self, item: str | dict[str, Any]) -> str:
        return "prose" if isinstance(item, str) else str(item.get("style", "prose"))
