# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads the JSON that the fact checker's model answers with, and nothing that is not exactly that shape."""

import json
from typing import Any, ClassVar

from engineering_influence.services.interfaces.fact_claim_parser_interface import (
    FactClaimParserInterface,
)


class FactClaimParser(FactClaimParserInterface):
    """A claim is an object with a ``claim`` and a ``query``, both text; a verdict has ``supported`` (true or false)
    and ``quote`` (text). The answer may be wrapped in a code fence or a sentence of preamble, but the JSON itself
    must parse and have exactly those types. A list of more than ``MAX_CLAIMS`` claims is cut to that many: a chapter
    that makes more than eight checkable claims is checked in part, and the report says so through the claims it
    keeps.
    """

    MAX_CLAIMS: ClassVar[int] = 8

    def claims(self, text: str) -> tuple[tuple[str, str], ...] | None:
        """The claims and their queries, in the order given, or None when the answer is not a list of them."""
        data = self._json(text, "[", "]")
        if not isinstance(data, list):
            return None
        claims: list[tuple[str, str]] = []
        for item in data[: self.MAX_CLAIMS]:
            if not isinstance(item, dict):
                return None
            claim, query = item.get("claim"), item.get("query")
            if not isinstance(claim, str) or not isinstance(query, str):
                return None
            if claim.strip() and query.strip():
                claims.append((claim.strip(), query.strip()))
        return tuple(claims)

    def verdict(self, text: str) -> tuple[bool, str] | None:
        """Whether the page supports the claim, and the quotation, or None when the answer is not that object."""
        data = self._json(text, "{", "}")
        if not isinstance(data, dict):
            return None
        supported, quote = data.get("supported"), data.get("quote")
        if not isinstance(supported, bool) or not isinstance(quote, str):
            return None
        return supported, quote.strip()

    @staticmethod
    def _json(text: str, opener: str, closer: str) -> Any:
        start, end = text.find(opener), text.rfind(closer)
        if start == -1 or end < start:
            return None
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None
