# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The credit line and source book a film's title page carries beyond its title, each optional."""

from dataclasses import dataclass
from typing import ClassVar

from engineering_influence.models.interfaces.screenplay_title_interface import (
    ScreenplayTitleInterface,
)


@dataclass(frozen=True, slots=True)
class ScreenplayTitle(ScreenplayTitleInterface):
    """`credit` prints as the Fountain Credit key and `source` as the Source key. Each is one line of plain text, at
    most `MAX_CHARS` characters, so that it cannot open a new element of the script."""

    MAX_CHARS: ClassVar[int] = 200

    credit: str | None = None
    source: str | None = None

    def __post_init__(self) -> None:
        """Validate the title page's lines when it is built."""
        for label, value in (("credit", self.credit), ("source", self.source)):
            if value is None:
                continue
            if not value.strip():
                raise ValueError(f"the title's {label} cannot be blank")
            if "\n" in value or "\r" in value:
                raise ValueError(f"the title's {label} is one line")
            if len(value) > self.MAX_CHARS:
                raise ValueError(f"the title's {label} is at most {self.MAX_CHARS} characters")

    def entries(self) -> tuple[tuple[str, str], ...]:
        """The title page's extra entries, in print order, for the ones given."""
        given = (("Credit", self.credit), ("Source", self.source))
        return tuple((key, value) for key, value in given if value is not None)
