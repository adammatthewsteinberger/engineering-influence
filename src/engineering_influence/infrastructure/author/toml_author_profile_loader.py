# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads an author profile from a TOML file, strictly."""

import tomllib
from pathlib import Path
from typing import Any

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.interfaces.author_profile_loader_interface import (
    AuthorProfileLoaderInterface,
)
from engineering_influence.models.author_profile import AuthorProfile


class TomlAuthorProfileLoader(AuthorProfileLoaderInterface):
    """The file holds ``author``, ``publisher``, ``edition`` and ``author_bio``, and may hold ``year``, ``website``,
    ``email``, ``isbn``, ``ebook_isbn``, ``dedication``, ``copyright_notes`` and ``also_by`` (a list of titles).

    Any other key is refused, so a misspelt one cannot quietly leave a field out, and a value of the wrong
    kind is refused rather than turned into text. A file larger than 64 KiB is refused unread, because a
    profile is a few paragraphs. Nothing in it is run, fetched or shown to a model.
    """

    TEXT = (
        "author",
        "publisher",
        "edition",
        "author_bio",
        "website",
        "email",
        "isbn",
        "ebook_isbn",
        "dedication",
        "copyright_notes",
    )
    KEYS = frozenset({*TEXT, "year", "also_by"})
    MAX_BYTES = 64 * 1024

    def load(self, path: Path) -> AuthorProfile | None:
        """The profile, None when there is no such file, or an ApplicationError when the file is not one."""
        if not path.is_file():
            return None
        if path.stat().st_size > self.MAX_BYTES:
            raise self._invalid(path, f"it is larger than {self.MAX_BYTES} bytes")
        try:
            raw = tomllib.loads(path.read_text(encoding="utf-8"))
        except (UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
            raise self._invalid(path, f"it is not valid UTF-8 TOML: {error}") from error
        unknown = sorted(raw.keys() - self.KEYS)
        if unknown:
            raise self._invalid(path, f"it has unknown keys {unknown}")
        values: dict[str, Any] = {}
        for key in self.TEXT:
            if key in raw:
                if not isinstance(raw[key], str):
                    raise self._invalid(path, f"{key} is text")
                values[key] = raw[key]
        if "year" in raw:
            if type(raw["year"]) is not int:
                raise self._invalid(path, "year is a whole number")
            values["year"] = raw["year"]
        if "also_by" in raw:
            titles = raw["also_by"]
            if not isinstance(titles, list) or not all(isinstance(title, str) for title in titles):
                raise self._invalid(path, "also_by is a list of titles")
            values["also_by"] = tuple(titles)
        try:
            return AuthorProfile(**values)
        except (TypeError, ValueError) as error:
            raise self._invalid(path, str(error)) from error

    @staticmethod
    def _invalid(path: Path, why: str) -> ApplicationError:
        return ApplicationError(
            code="AUTHOR_PROFILE_INVALID",
            message=f"the author profile {path} cannot be used: {why}",
            http_status=503,
        )
