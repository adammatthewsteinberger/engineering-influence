# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Writes evidence reports as indented JSON."""

import json
from pathlib import Path
from typing import Any


class JsonReport:
    """One format for every report the pipeline leaves behind."""

    def write(self, path: Path, data: dict[str, Any], *, ensure_ascii: bool = False) -> None:
        """Write data to path, creating parent directories."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(data, indent=2, ensure_ascii=ensure_ascii) + "\n", encoding="utf-8"
        )
