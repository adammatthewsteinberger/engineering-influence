# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A loaded EPUB archive: its documents, stylesheets, and package-level facts."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class EpubContents:
    """Everything the verification checks read, loaded once."""

    path: Path
    mimetype_ok: bool
    docs: dict[str, str]
    styles: dict[str, str]
    base: str
    opf_name: str
    opf_text: str
    nav_href: str
    nav_name: str
    nav: str
    ncx_name: str
