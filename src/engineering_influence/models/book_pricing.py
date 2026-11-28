# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What the author says the book costs, and where and when they checked."""

import re
from dataclasses import dataclass
from datetime import date
from typing import Any, ClassVar

from engineering_influence.models.interfaces.book_pricing_interface import BookPricingInterface


@dataclass(frozen=True, slots=True)
class BookPricing(BookPricingInterface):
    """The prices a strict release checks, which only the author can give.

    A price list is a decision and a fact about the market, so a run never invents one: the author supplies the
    date they checked the prices (``verified_on``, an ISO date), a page that shows the print cost (``source_url``)
    and the prices. The ebook and paperback prices are required; the hardcover price is optional, because not every
    trim size has a hardcover. Whether a price is a good one is for the release check to say, not this model.
    """

    URL: ClassVar[re.Pattern[str]] = re.compile(r"https?://[^\s<>\"']+")

    verified_on: str
    source_url: str
    ebook: float
    paperback: float
    hardcover: float | None = None

    def __post_init__(self) -> None:
        """Validate the prices when they are built."""
        try:
            date.fromisoformat(self.verified_on)
        except (TypeError, ValueError) as error:
            raise ValueError("verified_on is an ISO date, as in 2026-11-19") from error
        if not isinstance(self.source_url, str) or self.URL.fullmatch(self.source_url) is None:
            raise ValueError("source_url is one http or https address")
        for label, price in (("ebook", self.ebook), ("paperback", self.paperback)):
            self._price(label, price)
        if self.hardcover is not None:
            self._price("hardcover", self.hardcover)

    def entries(self) -> dict[str, Any]:
        """The ``[release.pricing]`` entries, in the order they are written; no hardcover price is left out."""
        found: dict[str, Any] = {
            "verified_on": self.verified_on,
            "source_url": self.source_url,
            "ebook": self.ebook,
            "paperback": self.paperback,
        }
        if self.hardcover is not None:
            found["hardcover"] = self.hardcover
        return found

    @staticmethod
    def _price(label: str, price: object) -> None:
        if isinstance(price, bool) or not isinstance(price, int | float) or not price > 0:
            raise ValueError(f"the {label} price is a number above zero")
