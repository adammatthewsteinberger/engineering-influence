# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a film's title.toml: the optional credit and source lines its title page carries."""

import tomllib
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.screenplay_title import ScreenplayTitle
from engineering_influence.services.interfaces.screenplay_title_parser_interface import (
    ScreenplayTitleParserInterface,
)


class ScreenplayTitleParser(ScreenplayTitleParserInterface):
    """The file has two optional keys, `credit` and `source`, each text. Any other key, or a value that is not text, is
    refused, so a typo does not silently print nothing on the title page.

    `ARTIFACT` is the name the run stores the file's text under.
    """

    ARTIFACT: ClassVar[str] = "title.toml"
    KEYS: ClassVar[frozenset[str]] = frozenset({"credit", "source"})

    def parse(self, text: str) -> ScreenplayTitle:
        """The file's title page entries, refused with a named reason when the file breaks the rules."""
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            raise self._invalid(f"it is not valid TOML: {error}") from error
        unknown = sorted(set(data) - self.KEYS)
        if unknown:
            raise self._invalid(f"it names keys the title page does not take: {', '.join(unknown)}")
        for key, value in data.items():
            if not isinstance(value, str):
                raise self._invalid(f"{key} must be text")
        try:
            return ScreenplayTitle(data.get("credit"), data.get("source"))
        except ValueError as error:
            raise self._invalid(str(error)) from error

    @classmethod
    def _invalid(cls, reason: str) -> ApplicationError:
        return ApplicationError(
            code="SCREENPLAY_TITLE_INVALID",
            message=f"{cls.ARTIFACT} {reason}",
            http_status=422,
        )
