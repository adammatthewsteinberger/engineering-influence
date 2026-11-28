# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The trim sizes a book can be printed at, and what KDP offers at each."""

from dataclasses import dataclass

from engineering_influence.errors.typesetting.manuscript_error import ManuscriptError
from engineering_influence.models.typesetting.interfaces.trim_size_interface import (
    TrimSizeInterface,
)

POINTS_PER_INCH = 72.0


@dataclass(frozen=True, slots=True)
class TrimSize(TrimSizeInterface):
    """A page size in inches, and whether KDP prints a hardcover at it.

    The hardcover column follows KDP's published hardcover trim list as of the date in the book's
    ``release.pricing.verified_on`` practice: check it again before relying on it, because KDP
    changes what it offers.
    """

    name: str
    width_in: float
    height_in: float
    hardcover: bool

    def __post_init__(self) -> None:
        """Validate the page size in inches when it is built."""
        if self.width_in <= 0 or self.height_in <= 0:
            raise ValueError("a trim size needs a positive width and height")

    @classmethod
    def for_name(cls, name: str | None) -> "TrimSize":
        """The trim size a config's ``trim_size`` names; a book that sets none is 6x9."""
        if name is None:
            return SIZES[DEFAULT]
        try:
            return SIZES[name]
        except KeyError:
            raise ManuscriptError(
                f"the trim size must be one of {', '.join(SIZES)}, not {name!r}"
            ) from None

    @classmethod
    def names(cls) -> tuple[str, ...]:
        """Every trim size name, in the order they are documented."""
        return tuple(SIZES)

    def points(self) -> tuple[float, float]:
        """Width and height in PDF points."""
        return (self.width_in * POINTS_PER_INCH, self.height_in * POINTS_PER_INCH)


DEFAULT = "6x9"
SIZES = {
    "5x8": TrimSize("5x8", 5.0, 8.0, hardcover=False),
    "5.5x8.5": TrimSize("5.5x8.5", 5.5, 8.5, hardcover=True),
    "6x9": TrimSize("6x9", 6.0, 9.0, hardcover=True),
}
