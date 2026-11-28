# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A file the author supplied as source material, read as text and refused when its text is not plain."""

import re
from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.source_file_interface import SourceFileInterface


@dataclass(frozen=True, slots=True)
class SourceFile(SourceFileInterface):
    """`name` is the file name, never a path; the text may hold tabs and line breaks, and no other control characters."""

    CONTROL: ClassVar[re.Pattern[str]] = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

    name: str
    body: str

    def __post_init__(self) -> None:
        """Refuse a file name that is a path, and text with control characters other than tabs and line breaks."""
        if not self.name or "/" in self.name or "\\" in self.name or self.name in (".", ".."):
            raise ValueError("a source file is named by its file name, not a path")
        if self.CONTROL.search(self.body):
            raise ValueError(
                f"source file {self.name!r} holds control characters, so it is refused"
            )

    def text(self) -> str:
        """The file's text."""
        return self.body
