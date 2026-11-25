# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a marketplace index from TOML, strictly."""

import tomllib
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.plugin_index_parser_interface import (
    PluginIndexParserInterface,
)
from engineering_influence.models.plugin_index import PluginIndex
from engineering_influence.models.plugin_index_entry import PluginIndexEntry


class TomlPluginIndexParser(PluginIndexParserInterface):
    """An index file has ``version = 1`` and any number of ``[[plugin]]`` tables.

    A ``[[plugin]]`` has ``name``, ``version``, ``url`` and ``sha256``, and an optional ``description``.
    Any other key is refused and named, and there is no key for anything but an address and a hash: an
    index cannot carry a command, a skill or a grant, so reading one cannot lead to any of them.
    """

    KEYS = frozenset({"name", "version", "description", "url", "sha256"})
    REQUIRED = frozenset({"name", "version", "url", "sha256"})

    def parse(self, data: bytes) -> PluginIndex:
        """The index, or an ApplicationError (PLUGIN_INDEX_INVALID) saying why the file is not one."""
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise self._invalid("it is not UTF-8 text") from error
        try:
            raw = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            raise self._invalid(f"it is not valid TOML: {error}") from error
        unknown = sorted(raw.keys() - {"version", "plugin"})
        if unknown:
            raise self._invalid(f"it has an unknown top-level key {unknown[0]!r}")
        version = raw.get("version")
        if type(version) is not int or version != PluginIndex.VERSION:  # True and 1.0 equal 1
            raise self._invalid(f"it is version {version!r}; this reads {PluginIndex.VERSION}")
        listed = raw.get("plugin", [])
        if not isinstance(listed, list):
            raise self._invalid("its plugin entries are [[plugin]] tables")
        entries = [self._entry(item, index) for index, item in enumerate(listed)]
        try:
            return PluginIndex(tuple(sorted(entries, key=lambda entry: entry.name)))
        except ValueError as error:
            raise self._invalid(str(error)) from error

    def _entry(self, item: Any, index: int) -> PluginIndexEntry:
        label = item.get("name", "?") if isinstance(item, dict) else "?"
        where = f"plugin #{index + 1} ({label})"
        if not isinstance(item, dict):
            raise self._invalid(f"{where} is not a table")
        unknown = sorted(set(item) - self.KEYS)
        if unknown:
            raise self._invalid(f"{where} has an unknown key {unknown[0]!r}")
        missing = sorted(self.REQUIRED - set(item))
        if missing:
            raise self._invalid(f"{where} is missing {missing[0]!r}")
        try:
            return PluginIndexEntry(
                name=item["name"],
                version=item["version"],
                url=item["url"],
                sha256=item["sha256"],
                description=item.get("description", ""),
            )
        except (TypeError, ValueError) as error:
            raise self._invalid(f"{where}: {error}") from error

    @staticmethod
    def _invalid(why: str) -> ApplicationError:
        return ApplicationError(
            code="PLUGIN_INDEX_INVALID", message=f"plugin index: {why}", http_status=422
        )
