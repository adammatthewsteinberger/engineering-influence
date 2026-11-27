# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads a bible card: its TOML front matter between two `+++` lines, then its Markdown. Also reads bible.toml's schema."""

import tomllib
from typing import ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.bible_card import BibleCard
from engineering_influence.models.bible_file import BibleFile
from engineering_influence.services.interfaces.bible_card_parser_interface import (
    BibleCardParserInterface,
)


class BibleCardParser(BibleCardParserInterface):
    """A card opens with a `+++` line, holds TOML, closes with a second `+++` line, and is Markdown after that. The schema is
    a bible.toml whose only table is `[required]`, mapping each kind to the list of keys its cards must set."""

    DELIMITER: ClassVar[str] = "+++"

    def card(self, file: BibleFile) -> BibleCard:
        """The card in the file, its body trimmed of the blank lines around it."""
        lines = file.text.splitlines()
        if not lines or lines[0].strip() != self.DELIMITER:
            raise self._invalid(file, "its first line must be a +++ line")
        end = self._closing(lines)
        if end is None:
            raise self._invalid(file, "its front matter needs a closing +++ line")
        try:
            fields = tomllib.loads("\n".join(lines[1:end]))
        except tomllib.TOMLDecodeError as error:
            raise self._invalid(file, f"its front matter is not valid TOML ({error})") from error
        return BibleCard(file.kind, file.id, fields, "\n".join(lines[end + 1 :]).strip())

    def schema(self, text: str) -> dict[str, tuple[str, ...]]:
        """The required keys by kind. A schema with anything but a `[required]` table of string lists is refused."""
        if not text.strip():
            return {}
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as error:
            raise self._schema_invalid(f"bible.toml is not valid TOML ({error})") from error
        required = data.get("required", {})
        well_formed = (
            set(data) <= {"required"}
            and isinstance(required, dict)
            and all(
                isinstance(keys, list) and all(isinstance(key, str) for key in keys)
                for keys in required.values()
            )
        )
        if not well_formed:
            raise self._schema_invalid(
                'bible.toml holds only a [required] table of kind = ["key", ...]'
            )
        return {kind: tuple(keys) for kind, keys in required.items()}

    def _closing(self, lines: list[str]) -> int | None:
        """The index of the closing `+++` line, searched after the opening one."""
        for index in range(1, len(lines)):
            if lines[index].strip() == self.DELIMITER:
                return index
        return None

    @staticmethod
    def _invalid(file: BibleFile, reason: str) -> ApplicationError:
        return ApplicationError(
            code="BIBLE_CARD_INVALID",
            message=f"{file.path()}: {reason}",
            http_status=422,
        )

    @staticmethod
    def _schema_invalid(reason: str) -> ApplicationError:
        return ApplicationError(code="BIBLE_SCHEMA_INVALID", message=reason, http_status=422)
