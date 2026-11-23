# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""JsonMarketplaceParser reads four things from a Claude Code marketplace file, classifies sources and follows none."""

import json

import pytest

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.infrastructure.plugins.json_marketplace_parser import (
    JsonMarketplaceParser,
)
from engineering_influence.interfaces.marketplace_listing_parser_interface import (
    MarketplaceListingParserInterface,
)

PARSER = JsonMarketplaceParser()


def parse(plugins: list[object], name: object = "Market", **extra: object) -> object:
    return PARSER.parse(json.dumps({"name": name, "plugins": plugins, **extra}).encode())


def refused(data: bytes) -> str:
    with pytest.raises(ApplicationError) as error:
        PARSER.parse(data)
    assert (error.value.code, error.value.http_status) == ("MARKETPLACE_INVALID", 422)
    return error.value.message


def test_it_is_a_parser() -> None:
    assert isinstance(PARSER, MarketplaceListingParserInterface)


def test_a_real_looking_marketplace_is_read_and_every_other_key_is_ignored() -> None:
    listing = parse(
        [
            {
                "name": "zeta",
                "source": "./z",
                "description": "Z plugin",
                "version": "1.2.0",
                "hooks": {"x": 1},
                "strict": False,
            },
            {"name": "alpha", "source": {"source": "github", "repo": "o/r", "ref": "v1"}},
        ],
        owner={"name": "Someone"},
        metadata={"x": 1},
    )
    assert listing.name == "Market" and listing.unreadable == 0  # type: ignore[attr-defined]
    alpha, zeta = listing.entries  # type: ignore[attr-defined]
    assert (alpha.name, alpha.kind, alpha.target, alpha.version) == (
        "alpha",
        "github",
        "o/r @ v1",
        "",
    )
    assert (zeta.identifier(), zeta.kind, zeta.target, zeta.description) == (
        "zeta@1.2.0",
        "path",
        "./z",
        "Z plugin",
    )


@pytest.mark.parametrize(
    ("source", "kind", "target"),
    [
        ("./plugins/x", "path", "./plugins/x"),
        ("plugins/x", "other", "plugins/x"),
        ("/etc", "other", "/etc"),
        ("./../x", "other", "./../x"),
        ("./a/../../x", "other", "./a/../../x"),
        ("./a..b/x", "path", "./a..b/x"),
        ({"source": "github", "repo": "o/r"}, "github", "o/r"),
        ({"source": "github", "repo": "o/r", "ref": 3}, "github", "o/r"),
        ({"source": "github"}, "other", "github"),
        ({"source": "url", "url": "https://g.example/r.git"}, "url", "https://g.example/r.git"),
        ({"source": "git", "url": "git@g.example:r.git"}, "url", "git@g.example:r.git"),
        ({"source": "url"}, "other", "url"),
        ({"source": "git-subdir", "url": "x"}, "other", "git-subdir"),
        ({}, "other", "None"),
        (7, "other", "no source"),
        (None, "other", "no source"),
    ],
)
def test_a_source_is_classified_and_never_followed(source: object, kind: str, target: str) -> None:
    (entry,) = parse([{"name": "p", "source": source}]).entries  # type: ignore[attr-defined]
    assert (entry.kind, entry.target) == (kind, target)


def test_a_long_other_source_is_cut() -> None:
    (entry,) = parse([{"name": "p", "source": "x" * 500}]).entries  # type: ignore[attr-defined]
    assert entry.target == "x" * 300
    (entry,) = parse([{"name": "p", "source": {"source": "y" * 500}}]).entries  # type: ignore[attr-defined]
    assert entry.target == "y" * 100


def test_entries_that_cannot_be_read_are_counted_and_the_rest_stay() -> None:
    listing = parse(
        [
            "not a table",
            {"source": "./x"},
            {"name": "", "source": "./x"},
            {"name": 3, "source": "./x"},
            {"name": "bad\nname", "source": "./x"},
            {"name": "n" * 101, "source": "./x"},
            {"name": "good", "source": "./g"},
            {"name": "good", "source": "./other"},
            {"name": "tgt", "source": {"source": "url", "url": "u" * 301}},
        ]
    )
    assert [entry.name for entry in listing.entries] == ["good"]  # type: ignore[attr-defined]
    assert listing.entries[0].target == "./g" and listing.unreadable == 8  # type: ignore[attr-defined]


def test_a_description_is_flattened_to_one_line_and_cut_at_a_word() -> None:
    plain, long, odd = parse(
        [
            {"name": "a", "source": "./a", "description": "line one\n\tline\x00two"},
            {"name": "b", "source": "./b", "description": "word " * 100},
            {"name": "c", "source": "./c", "description": 5, "version": 5},
        ]
    ).entries  # type: ignore[attr-defined]
    assert plain.description == "line one line two"
    assert len(long.description) <= 300 and long.description.endswith("word...")
    assert (odd.description, odd.version) == ("", "")


def test_a_description_of_exactly_the_limit_is_kept_whole() -> None:
    (entry,) = parse([{"name": "a", "source": "./a", "description": "d" * 300}]).entries  # type: ignore[attr-defined]
    assert entry.description == "d" * 300


def test_an_empty_marketplace_is_fine() -> None:
    assert parse([]).entries == ()  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("data", "why"),
    [
        (b"{nope", "it is not valid JSON text"),
        (b"\xff\xfe", "it is not valid JSON text"),
        (b"[" * 100_000, "it is not valid JSON text"),
        (b"[]", "it is a JSON object with a list of plugins"),
        (b'{"name": "x"}', "it is a JSON object with a list of plugins"),
        (b'{"name": "x", "plugins": {}}', "it is a JSON object with a list of plugins"),
        (b'{"plugins": []}', "it has a one-line name"),
        (b'{"name": 3, "plugins": []}', "it has a one-line name"),
        (b'{"name": " ", "plugins": []}', "it has a one-line name"),
        (b'{"name": "a\\nb", "plugins": []}', "it has a one-line name"),
    ],
)
def test_a_file_that_is_not_a_marketplace_is_refused(data: bytes, why: str) -> None:
    assert refused(data) == f"marketplace file: {why}"


def test_more_plugins_than_a_listing_holds_is_refused() -> None:
    plugins = [{"name": f"p{n:03d}", "source": "./p"} for n in range(501)]
    assert "at most 500 entries" in refused(json.dumps({"name": "x", "plugins": plugins}).encode())
