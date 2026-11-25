# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).

"""FactClaimParser: the checker's JSON is read exactly, and anything that is not that shape is refused, never guessed."""

import pytest

from engineering_influence.services.fact_claim_parser import FactClaimParser
from engineering_influence.services.interfaces.fact_claim_parser_interface import (
    FactClaimParserInterface,
)

PARSER = FactClaimParser()


def test_a_list_of_claims_is_read_with_its_queries_in_order() -> None:
    text = '[{"claim": "Bees fly 20 km", "query": "bee flight range"}, {"claim": "A hive has 50,000 bees", "query": "hive size"}]'
    assert PARSER.claims(text) == (
        ("Bees fly 20 km", "bee flight range"),
        ("A hive has 50,000 bees", "hive size"),
    )


def test_an_empty_list_is_no_claims() -> None:
    assert PARSER.claims("[]") == ()


def test_a_code_fence_and_a_preamble_are_skipped_around_the_json() -> None:
    text = 'Here is the list:\n```json\n[{"claim": "Bees dance", "query": "bee dance"}]\n```'
    assert PARSER.claims(text) == (("Bees dance", "bee dance"),)


def test_more_than_eight_claims_keeps_the_first_eight() -> None:
    items = ", ".join(f'{{"claim": "claim {n}", "query": "q{n}"}}' for n in range(10))
    claims = PARSER.claims(f"[{items}]")
    assert claims is not None and len(claims) == 8 and claims[-1] == ("claim 7", "q7")


def test_a_blank_claim_or_query_is_dropped_rather_than_checked() -> None:
    text = '[{"claim": "  ", "query": "q"}, {"claim": "Real", "query": " real "}]'
    assert PARSER.claims(text) == (("Real", "real"),)


@pytest.mark.parametrize(
    "text",
    [
        "no json at all",
        "[not json]",
        '{"claim": "a", "query": "b"}',
        '[{"claim": 1, "query": "b"}]',
        '[{"claim": "a"}]',
        '["a claim"]',
        "] before [",
    ],
)
def test_text_that_is_not_a_list_of_claims_is_none(text: str) -> None:
    assert PARSER.claims(text) is None


def test_a_verdict_is_read_with_its_quotation() -> None:
    assert PARSER.verdict('{"supported": true, "quote": " Bees dance. "}') == (True, "Bees dance.")
    assert PARSER.verdict('{"supported": false, "quote": ""}') == (False, "")


@pytest.mark.parametrize(
    "text",
    [
        "nothing here",
        '["supported"]',
        '{"supported": "yes", "quote": "x"}',
        '{"supported": true, "quote": 3}',
        '{"supported": true}',
        '{"supported": true, "quote": "x"',
    ],
)
def test_text_that_is_not_a_verdict_is_none(text: str) -> None:
    assert PARSER.verdict(text) is None


def test_it_is_a_fact_claim_parser() -> None:
    assert isinstance(PARSER, FactClaimParserInterface)
