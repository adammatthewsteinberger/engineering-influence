# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The back cover text does not fit above the barcode area."""

from engineering_influence.errors.typesetting.book_build_error import BookBuildError
from engineering_influence.errors.typesetting.interfaces.back_cover_text_too_long_error_interface import (
    BackCoverTextTooLongErrorInterface,
)


class BackCoverTextTooLongError(BackCoverTextTooLongErrorInterface, BookBuildError):
    """Raised when the description, even at the smallest type, would run into the barcode area.

    It carries the numbers a person, or a model asked to shorten the text, needs: how long the
    description is, how many characters fit at this trim size, and how far it overflows.
    """

    def __init__(self, characters: int, capacity: int, overflow_in: float) -> None:
        self.characters = characters
        self.capacity = capacity
        self.overflow_in = overflow_in
        super().__init__(
            "the back cover text does not fit above the barcode area: the description has "
            f"{characters} characters and about {capacity} fit at this trim size, even at the "
            f"smallest type; it overflows by {overflow_in:.2f} in. Shorten the description or "
            "the author bio."
        )
