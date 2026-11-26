# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The outcome of typesetting a screenplay: whether LaTeX finished, the PDF it made, its pages and the log's tail."""

from dataclasses import dataclass

from engineering_influence.models.interfaces.screenplay_typeset_interface import (
    ScreenplayTypesetInterface,
)


@dataclass(frozen=True, slots=True)
class ScreenplayTypeset(ScreenplayTypesetInterface):
    """`status` is the LaTeX exit status (0 when it finished); `pdf` and `pages` are empty or zero when it did not."""

    status: int
    pdf: bytes
    pages: int
    log: str

    def __post_init__(self) -> None:
        if self.status == 0 and (not self.pdf or self.pages < 1):
            raise ValueError("a finished typesetting has a PDF with at least one page")
