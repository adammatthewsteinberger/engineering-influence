"""Shared loader for the sample project fixture used by every example."""

import json
from pathlib import Path
from typing import Any


class SampleProject:
    """Reads the bundled sample project."""

    PATH = Path(__file__).parent / "sample_project" / "project.json"

    def load(self) -> dict[str, Any]:
        """Return the sample project as a plain dictionary."""
        data: dict[str, Any] = json.loads(self.PATH.read_text(encoding="utf-8"))
        return data
