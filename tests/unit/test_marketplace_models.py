# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""MarketplaceEntry and MarketplaceListing hold text to read and refuse anything that could be mistaken for more."""

import pytest

from engineering_influence.models.interfaces.marketplace_entry_interface import (
    MarketplaceEntryInterface,
)
from engineering_influence.models.interfaces.marketplace_listing_interface import (
    MarketplaceListingInterface,
)
from engineering_influence.models.marketplace_entry import MarketplaceEntry
from engineering_influence.models.marketplace_listing import MarketplaceListing


def entry(name: str = "alpha", **changes: object) -> MarketplaceEntry:
    values: dict[str, object] = {"description": "d", "kind": "path", "target": "./a"}
    values.update(changes)
    return MarketplaceEntry(name, **values)  # type: ignore[arg-type]


def test_an_entry_names_itself_with_its_version_when_it_has_one() -> None:
    assert isinstance(entry(), MarketplaceEntryInterface)
    assert entry().identifier() == "alpha" and entry(version="3").identifier() == "alpha@3"


@pytest.mark.parametrize(
    "changes",
    [
        {"name": ""},
        {"name": "x" * 101},
        {"name": "a\nb"},
        {"name": 3},
        {"description": "x" * 301},
        {"description": "a\tb"},
        {"target": "x" * 301},
        {"target": "a\nb"},
        {"version": "v" * 51},
        {"version": "a\nb"},
        {"local": "/x\n"},
        {"kind": "git"},
        {"kind": "github", "local": "/x"},
    ],
)
def test_an_entry_that_is_not_one_line_of_text_or_has_an_unknown_source_is_refused(
    changes: dict[str, object],
) -> None:
    name = changes.pop("name", "alpha")
    with pytest.raises(ValueError):
        entry(name, **changes)  # type: ignore[arg-type]


def test_an_entry_at_every_limit_is_fine() -> None:
    made = MarketplaceEntry("n" * 100, "d" * 300, "path", "t" * 300, "v" * 50, "/" + "l" * 999)
    assert made.local.startswith("/")


def test_a_listing_searches_names_and_descriptions_ignoring_case() -> None:
    listing = MarketplaceListing(
        "Team", (entry("alpha", description="Sources"), entry("beta", description="Style"))
    )
    assert isinstance(listing, MarketplaceListingInterface)
    assert [e.name for e in listing.search(" SOURCE ")] == ["alpha"]
    assert [e.name for e in listing.search("BET")] == ["beta"]
    assert len(listing.search("")) == 2 and listing.search("zzz") == ()


@pytest.mark.parametrize(
    "build",
    [
        lambda: MarketplaceListing(""),
        lambda: MarketplaceListing(" "),
        lambda: MarketplaceListing("a\nb"),
        lambda: MarketplaceListing(3),  # type: ignore[arg-type]
        lambda: MarketplaceListing("t", [entry()]),  # type: ignore[arg-type]
        lambda: MarketplaceListing("t", (entry("b"), entry("a"))),
        lambda: MarketplaceListing("t", (entry("a"), entry("a"))),
        lambda: MarketplaceListing("t", (), -1),
        lambda: MarketplaceListing("t", (), True),  # type: ignore[arg-type]
        lambda: MarketplaceListing("t", tuple(entry(f"p{n:03d}") for n in range(501))),
    ],
)
def test_a_listing_that_is_not_shaped_right_is_refused(build: object) -> None:
    with pytest.raises((ValueError, TypeError)):
        build()  # type: ignore[operator]


def test_a_listing_of_exactly_the_most_entries_is_fine() -> None:
    assert (
        len(MarketplaceListing("t", tuple(entry(f"p{n:03d}") for n in range(500))).entries) == 500
    )
