# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reads the story bible stage's JSON into a story bible, strictly."""

import json
import unicodedata
from typing import Any, ClassVar

from engineering_influence.errors.application_error import ApplicationError
from engineering_influence.models.story_bible import StoryBible
from engineering_influence.models.story_character import StoryCharacter
from engineering_influence.models.story_event import StoryEvent
from engineering_influence.services.interfaces.story_bible_parser_interface import (
    StoryBibleParserInterface,
)


class StoryBibleParser(StoryBibleParserInterface):
    """The contract between the story bible stage and every stage that checks a chapter against it.

    The stage is told to answer with one JSON object with the keys ``premise``, ``characters`` (each with ``name``,
    ``aliases`` and ``age``), ``places``, ``timeline`` (each with ``when`` and ``label``) and ``span_years``. This
    reads the first JSON object in the text, so a preamble or a code fence around it does no harm, and nothing
    after it is read. A key it does not know is ignored, because nothing here acts on it; a value of the wrong type,
    or a bible that breaks the bible's own rules (a name twice, too many characters), is refused with a message that
    says which, so the person (or the stage that wrote it) can see why.

    What the model wrote is untrusted, so every text has its line breaks and runs of spaces collapsed and the
    characters that render as nothing or act as controls removed before the bible's own limits are applied. The
    timeline is put in the order of its ``when`` values, because a model lists events as they occur to it.
    The result is data; it is never run.
    """

    HIDDEN: ClassVar[frozenset[str]] = frozenset({"Cc", "Cf", "Cs", "Co", "Cn"})

    def parse(self, text: str) -> StoryBible:
        """The bible, or an ApplicationError (STORY_BIBLE_INVALID) saying what is wrong with the text."""
        data = self._object(text)
        try:
            return StoryBible(
                premise=self._text(data.get("premise"), "the premise"),
                characters=tuple(
                    self._character(item, number)
                    for number, item in enumerate(self._list(data, "characters"), start=1)
                ),
                places=tuple(
                    self._text(item, f"place {number}")
                    for number, item in enumerate(self._list(data, "places"), start=1)
                ),
                timeline=tuple(
                    sorted(
                        (
                            self._event(item, number)
                            for number, item in enumerate(self._list(data, "timeline"), start=1)
                        ),
                        key=lambda event: event.when,
                    )
                ),
                span_years=self._whole(data.get("span_years", 0), "span_years"),
            )
        except ValueError as error:
            raise self._invalid(str(error)) from error

    def _object(self, text: str) -> dict[str, Any]:
        start = text.find("{")
        if start < 0:
            raise self._invalid("there is no JSON object in the answer")
        try:
            value, _ = json.JSONDecoder().raw_decode(text, start)
        except json.JSONDecodeError as error:
            raise self._invalid(
                f"the JSON is not valid ({error.msg} at position {error.pos})"
            ) from error
        return value  # type: ignore[no-any-return]

    def _list(self, data: dict[str, Any], key: str) -> list[Any]:
        value = data.get(key, [])
        if not isinstance(value, list):
            raise self._invalid(f"{key} is not a list")
        return value

    def _character(self, item: Any, number: int) -> StoryCharacter:
        if not isinstance(item, dict):
            raise self._invalid(f"character {number} is not an object")
        aliases = item.get("aliases", [])
        if not isinstance(aliases, list):
            raise self._invalid(f"character {number}'s aliases are not a list")
        age = item.get("age")
        return StoryCharacter(
            name=self._text(item.get("name"), f"character {number}'s name"),
            aliases=tuple(self._text(alias, f"character {number}'s alias") for alias in aliases),
            age=None if age is None else self._whole(age, f"character {number}'s age"),
        )

    def _event(self, item: Any, number: int) -> StoryEvent:
        if not isinstance(item, dict):
            raise self._invalid(f"event {number} is not an object")
        return StoryEvent(
            when=self._whole(item.get("when"), f"event {number}'s time"),
            label=self._text(item.get("label"), f"event {number}'s label"),
        )

    def _text(self, value: Any, label: str) -> str:
        if not isinstance(value, str):
            raise self._invalid(f"{label} is not text")
        spaced = "".join(" " if char.isspace() else char for char in value)
        shown = "".join(char for char in spaced if unicodedata.category(char) not in self.HIDDEN)
        return " ".join(shown.split())

    def _whole(self, value: Any, label: str) -> int:
        if type(value) is not int:
            raise self._invalid(f"{label} is not a whole number")
        return value

    @staticmethod
    def _invalid(why: str) -> ApplicationError:
        return ApplicationError(
            code="STORY_BIBLE_INVALID",
            message=f"the story bible cannot be read: {why}",
            http_status=422,
        )
