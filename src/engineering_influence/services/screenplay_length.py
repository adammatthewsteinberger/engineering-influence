# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Length of a screenplay against the running time of the film: about one page a minute (ledger decision F8)."""

from typing import ClassVar

from engineering_influence.services.interfaces.screenplay_length_interface import (
    ScreenplayLengthInterface,
)


class ScreenplayLength(ScreenplayLengthInterface):
    """Pages are the rendered screenplay's page count (the KDP PDF), which is what the length is measured in.

    The ceiling is `CEILING_PAGES`, the top of the range decided in F8 (195 pages, about three hours and a quarter).
    A screenplay over `THREE_HOURS_PAGES` (180 pages, three hours at one page a minute) is reported as a note, not a
    failure, so the author can see which films run past three hours before deciding what to cut.
    """

    CEILING_PAGES: ClassVar[int] = 195
    THREE_HOURS_PAGES: ClassVar[int] = 180

    def __init__(self, ceiling_pages: int = CEILING_PAGES) -> None:
        if ceiling_pages < 1:
            raise ValueError("a screenplay's page ceiling is a positive number of pages")
        self._ceiling = ceiling_pages

    def problems(self, pages: int) -> tuple[str, ...]:
        """A failure when the screenplay is over the ceiling; a note when it is past three hours."""
        if pages < 1:
            return (f"the screenplay has {pages} pages, which is not a screenplay",)
        if pages > self._ceiling:
            return (
                f"{pages} pages is over the {self._ceiling}-page ceiling (about three hours and a quarter)",
            )
        if pages > self.THREE_HOURS_PAGES:
            return (
                f"{pages} pages is past three hours (about {pages} minutes at one page a minute)",
            )
        return ()
