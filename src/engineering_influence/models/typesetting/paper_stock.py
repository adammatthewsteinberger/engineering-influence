# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The interior paper a book is printed on, which decides how thick the spine is."""

from dataclasses import dataclass

from engineering_influence.errors.typesetting.manuscript_error import ManuscriptError
from engineering_influence.models.typesetting.interfaces.paper_stock_interface import (
    PaperStockInterface,
)


@dataclass(frozen=True, slots=True)
class PaperStock(PaperStockInterface):
    """A paper and the spine width each of its pages adds, in inches.

    KDP's black-ink thicknesses: white paper 0.002252 in a page, cream paper 0.0025 in a page.
    Cream is thicker, so a cream book's spine is wider than a white book's of the same length.
    """

    name: str
    inches_per_page: float

    def __post_init__(self) -> None:
        if self.inches_per_page <= 0:
            raise ValueError("paper needs a positive thickness")

    @classmethod
    def for_name(cls, name: str | None) -> "PaperStock":
        """The paper a config's ``paper`` names; a book that sets none is on white paper."""
        if name is None:
            return STOCKS[DEFAULT]
        try:
            return STOCKS[name]
        except KeyError:
            raise ManuscriptError(
                f"the paper must be one of {', '.join(STOCKS)}, not {name!r}"
            ) from None

    @classmethod
    def names(cls) -> tuple[str, ...]:
        """Every paper name, in the order they are documented."""
        return tuple(STOCKS)


DEFAULT = "white"
STOCKS = {
    "white": PaperStock("white", 0.002252),
    "cream": PaperStock("cream", 0.0025),
}
