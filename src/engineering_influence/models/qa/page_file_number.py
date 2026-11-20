# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Page numbers parsed from rendered file names."""

import re
from pathlib import Path


class PageFileNumber:
    """Natural ordering for names such as render-0012.png."""

    def of(self, path: Path) -> int:
        """The trailing number of a .png file name, or 0 when there is none."""
        match = re.search(r"(\d+)(?:\.png)$", path.name)
        return int(match.group(1)) if match else 0
