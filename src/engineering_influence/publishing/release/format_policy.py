# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which output formats a book declares."""

from typing import Any


class FormatPolicy:
    """Keeps old books compatible: no [formats] table means no hardcover."""

    def of(self, config: dict[str, Any]) -> dict[str, Any]:
        """The explicit format policy."""
        formats = config.get("formats", {})
        return {
            "hardcover": bool(formats.get("hardcover", False)),
            "hardcover_max_pages": int(formats.get("hardcover_max_pages", 550)),
        }
