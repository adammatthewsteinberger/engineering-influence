# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a Claude Code ``marketplace.json``."""

import json
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.marketplace_listing_parser_interface import (
    MarketplaceListingParserInterface,
)
from engineering_influence.models.marketplace_entry import MarketplaceEntry
from engineering_influence.models.marketplace_listing import MarketplaceListing


class JsonMarketplaceParser(MarketplaceListingParserInterface):
    """Takes four things from each plugin (name, description, version, source) and ignores every other key.

    A real marketplace file has many more keys (owner, metadata, commands, hooks, ``strict``); none of them is read,
    because none can change what is shown or what is done. A source is classified, never followed: a string starting
    ``./`` is a ``path`` (refused as ``other`` if it climbs out with ``..``), ``{"source": "github"}`` a repository,
    ``{"source": "url"}`` or ``"git"`` an address, and anything else ``other``. An entry that cannot be read is
    counted and left out, so one odd entry does not hide the rest; a duplicate name keeps the first.
    """

    def parse(self, data: bytes) -> MarketplaceListing:
        """The listing."""
        try:
            raw = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, ValueError, RecursionError) as error:
            raise self._invalid("it is not valid JSON text") from error
        if not isinstance(raw, dict) or not isinstance(raw.get("plugins"), list):
            raise self._invalid("it is a JSON object with a list of plugins")
        name = raw.get("name")
        if not isinstance(name, str) or not name.strip() or not name.isprintable():
            raise self._invalid("it has a one-line name")
        found: dict[str, MarketplaceEntry] = {}
        unreadable = 0
        for item in raw["plugins"]:
            entry = self._entry(item)
            if entry is None or entry.name in found:
                unreadable += 1
            else:
                found[entry.name] = entry
        try:
            return MarketplaceListing(name, tuple(found[key] for key in sorted(found)), unreadable)
        except ValueError as error:
            raise self._invalid(str(error)) from error

    def _entry(self, item: Any) -> MarketplaceEntry | None:
        if not isinstance(item, dict):
            return None
        kind, target = self._source(item.get("source"))
        description = item.get("description", "")
        version = item.get("version", "")
        try:
            return MarketplaceEntry(
                name=item.get("name", ""),
                description=self._line(description) if isinstance(description, str) else "",
                kind=kind,
                target=target,
                version=version if isinstance(version, str) else "",
            )
        except ValueError:
            return None

    @staticmethod
    def _line(text: str) -> str:
        flat = " ".join("".join(c if c.isprintable() else " " for c in text).split())
        limit = MarketplaceEntry.MAX_DESCRIPTION_CHARS
        return flat if len(flat) <= limit else flat[: limit - 3].rsplit(" ", 1)[0].rstrip() + "..."

    @staticmethod
    def _source(source: Any) -> tuple[str, str]:
        if isinstance(source, str):
            if source.startswith("./") and ".." not in source.split("/"):
                return "path", source
            return "other", source[:300]
        if not isinstance(source, dict):
            return "other", "no source"
        kind = source.get("source")
        if kind == "github" and isinstance(source.get("repo"), str):
            ref = source.get("ref") if isinstance(source.get("ref"), str) else ""
            return "github", source["repo"] + (f" @ {ref}" if ref else "")
        if kind in ("url", "git") and isinstance(source.get("url"), str):
            return "url", source["url"]
        return "other", str(kind)[:100]

    @staticmethod
    def _invalid(why: str) -> ApplicationError:
        return ApplicationError(
            code="MARKETPLACE_INVALID", message=f"marketplace file: {why}", http_status=422
        )
