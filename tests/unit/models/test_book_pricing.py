"""BookPricing: the prices a strict release checks, which only the author can give."""

from typing import Any

import pytest

from engineering_influence.models.book_pricing import BookPricing
from engineering_influence.models.interfaces.book_pricing_interface import BookPricingInterface


def pricing(**changes: Any) -> BookPricing:
    fields: dict[str, Any] = {
        "verified_on": "2026-11-19",
        "source_url": "https://kdp.example/print-costs",
        "ebook": 4.99,
        "paperback": 12.99,
    }
    return BookPricing(**{**fields, **changes})


def refused(**changes: Any) -> str:
    with pytest.raises(ValueError) as error:
        pricing(**changes)
    return str(error.value)


def test_the_entries_are_written_in_a_fixed_order_and_the_hardcover_is_optional() -> None:
    made = pricing()
    assert isinstance(made, BookPricingInterface)
    assert list(made.entries()) == ["verified_on", "source_url", "ebook", "paperback"]
    assert pricing(hardcover=22.99).entries()["hardcover"] == 22.99


def test_the_date_is_an_iso_date_the_source_one_address_and_each_price_above_zero() -> None:
    assert "ISO date" in refused(verified_on="last week")
    assert "ISO date" in refused(verified_on=None)
    assert "one http or https address" in refused(source_url="kdp.example")
    assert "one http or https address" in refused(source_url="https://a.example https://b.example")
    assert "one http or https address" in refused(source_url=None)
    for label in ("ebook", "paperback", "hardcover"):
        assert refused(**{label: 0}) == f"the {label} price is a number above zero"
        assert refused(**{label: -1.0}) == f"the {label} price is a number above zero"
        assert refused(**{label: "5"}) == f"the {label} price is a number above zero"
        assert refused(**{label: True}) == f"the {label} price is a number above zero"
